from obswebsocket import obsws, requests
import obswebsocket
from loguru import logger as log
import websocket
import socket
import ipaddress

# Monkeypatch obswebsocket to prevent reconnect thread from dying on WebSocketExceptions or other transient errors
from obswebsocket.core import ReconnectThread

original_connect = obsws.connect

def wrapped_connect(self):
    try:
        original_connect(self)
    except (socket.error, websocket.WebSocketException, Exception) as e:
        if self.authreconnect:
            if not getattr(self, "thread_reco", None):
                log.warning(f"Connection failed: {e}. Reconnecting in {self.authreconnect} second(s).")
                self.thread_reco = ReconnectThread(self)
                self.thread_reco.daemon = True
                self.thread_reco.start()
            else:
                log.warning(f"Connection failed: {e}. Reconnect timer already running.")
        else:
            from obswebsocket import exceptions
            raise exceptions.ConnectionFailure(str(e))

obsws.connect = wrapped_connect

original_reconnect = obsws.reconnect

def wrapped_reconnect(self):
    try:
        original_reconnect(self)
    except Exception as e:
        log.warning(f"Error during reconnect: {e}. Retrying in {self.authreconnect} second(s).")
        if not getattr(self, "thread_reco", None):
            self.thread_reco = ReconnectThread(self)
            self.thread_reco.daemon = True
            self.thread_reco.start()

obsws.reconnect = wrapped_reconnect


class OBSEventController(obsws):
    def _auth(self):
        import json
        from obswebsocket import exceptions
        
        message = self.ws.recv()
        log.debug("Got Hello message in OBSEventController: {}".format(message))
        result = json.loads(message)

        if result.get('op') != 0:
            raise exceptions.ConnectionFailure(result.get('error', "Invalid Hello message."))
        self.server_version = result['d'].get('obsWebSocketVersion')

        if result['d'].get('authentication'):
            auth = self._build_auth_string(result['d']['authentication']['salt'], result['d']['authentication']['challenge'])
        else:
            auth = ''

        payload = {
            "op": 1,
            "d": {
                "rpcVersion": 1,
                "authentication": auth,
                "eventSubscriptions": 1023 | (1 << 16)  # EventSubscription::All (1023) | InputVolumeMeters (65536)
            }
        }
        log.debug("Sending Identify message: {}".format(json.dumps(payload)))
        self.ws.send(json.dumps(payload))

        message = self.ws.recv()
        if not message:
            raise exceptions.ConnectionFailure("Empty response to Identify, password may be incorrect.")
        log.debug("Got Identified message: {}".format(message))
        result = json.loads(message)
        if result.get('op') != 2:
            raise exceptions.ConnectionFailure(result.get('error', "Invalid Identified message."))
        if result['d'].get('negotiatedRpcVersion') != 1:
            raise exceptions.ConnectionFailure(result.get('error', "Invalid RPC version negotiated."))

class OBSController(obsws):
    def __init__(self):
        self._connected_state = False
        self.event_obs: obsws = None # All events are connected to this to avoid crash if a request is made in an event
        self.volume_meters = {}
        pass

    @property
    def connected(self) -> bool:
        req_conn = self.ws is not None and getattr(self.ws, "connected", False)
        evt_conn = self.event_obs is not None and self.event_obs.ws is not None and getattr(self.event_obs.ws, "connected", False)
        return req_conn and evt_conn

    @connected.setter
    def connected(self, value):
        self._connected_state = value

    def validate_ip(self, host: str):
        if not host:
            return False
        if host in ("localhost", "127.0.0.1", "::1"):
            return True

        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            pass

        try:
            socket.getaddrinfo(host, None)
            return True
        except socket.gaierror:
            return False

    def on_connect(self, obs):
        self.connected = True

    def on_disconnect(self, obs):
        self.connected = False

    def register(self, *args, **kwargs):
        """
        Pass all event register calls to the event_obs.
        This avoids crashes if a request is made in an event
        """
        try:
            self.event_obs.register(*args, **kwargs)
        except Exception as e:
            log.error(e)

    def on_volume_meters(self, event):
        try:
            inputs = event.datain.get("inputs", [])
            for inp in inputs:
                name = inp.get("inputName")
                levels = inp.get("inputLevelsMul", [])
                if name and levels:
                    peaks = []
                    for channel in levels:
                        try:
                            peaks.append(channel[1])
                        except (IndexError, TypeError):
                            try:
                                peaks.append(channel[0])
                            except (IndexError, TypeError):
                                if isinstance(channel, (int, float)):
                                    peaks.append(channel)
                    if peaks:
                        self.volume_meters[name] = max(peaks)
        except Exception as e:
            log.error(f"Error in on_volume_meters: {e}")

    def connect_to(self, host=None, port=None, timeout=1, legacy=False, **kwargs):
        # Disconnect existing connections if any, to avoid resource leaks
        try:
            self.disconnect()
        except Exception:
            pass
        if self.event_obs is not None:
            try:
                self.event_obs.disconnect()
            except Exception:
                pass

        if not self.validate_ip(host):
            log.error("Invalid IP address for OBS connection")
            return False

        try:
            log.debug(f"Trying to connect to obs with legacy: {legacy}")
            super().__init__(host=host, port=port, timeout=timeout, legacy=legacy, on_connect=self.on_connect, on_disconnect=self.on_disconnect, authreconnect=5, **kwargs)
            self.event_obs = OBSEventController(host=host, port=port, timeout=timeout, legacy=legacy, on_connect=self.on_connect, on_disconnect=self.on_disconnect, authreconnect=5, **kwargs)
            self.connect()
            try:
                self.event_obs.connect()
                self.event_obs.register(self.on_volume_meters, obswebsocket.events.InputVolumeMeters)
            except Exception as e:
                log.error(f"Failed to connect event_obs: {e}")
            log.info("Successfully connected to OBS")
            return True
        except (obswebsocket.exceptions.ConnectionFailure, ValueError) as e:
            try:
                log.error(f"Failed to connect to OBS with legacy: {legacy}, trying with legacy: {not legacy}")
                super().__init__(host=host, port=port, timeout=timeout, legacy=not legacy, on_connect=self.on_connect, on_disconnect=self.on_disconnect, authreconnect=5, **kwargs)
                self.event_obs = OBSEventController(host=host, port=port, timeout=timeout, legacy=not legacy, on_connect=self.on_connect, on_disconnect=self.on_disconnect, authreconnect=5, **kwargs)
                self.connect()
                try:
                    self.event_obs.connect()
                    self.event_obs.register(self.on_volume_meters, obswebsocket.events.InputVolumeMeters)
                except Exception as e:
                    log.error(f"Failed to connect event_obs: {e}")
                log.info("Successfully connected to OBS")
                return True

            # ValueError: invalid port etc
            except (obswebsocket.exceptions.ConnectionFailure, ValueError) as e:
                log.error(f"Failed to connect to OBS: {e}")
                if self.connected:
                    self.disconnect()
                if self.event_obs is not None:
                    try:
                        self.event_obs.disconnect()
                    except Exception:
                        pass
                return False


    ## Streaming
    def start_stream(self) -> None:
        try:
            self.call(requests.StartStream())
        except Exception as e:
            log.error(e)

    def stop_stream(self) -> None:
        try:
            self.call(requests.StopStream())
        except Exception as e:
            log.error(e)

    def toggle_stream(self):
        """
        outputActive: bool -> The new state of the stream
        """
        try:
            self.call(requests.ToggleStream())
        except Exception as e:
            log.error(e)

    def get_stream_status(self) -> bool:
        """
        outputActive: bool -> Whether streaming is active
        outputReconnecting: bool -> Whether streaming is reconnecting
        outputTimecode: str -> The current timecode of the stream
        outputDuration: int -> The duration of the stream in milliseconds
        outputCongestion: int -> The congestion of the stream
        outputBytes: int -> The number of bytes written to the stream
        outputSkippedFrames: int -> The number of skipped frames
        outputTotalFrames: int -> The total number of delivered frames
        """
        try:
            return self.call(requests.GetStreamStatus())
        except Exception as e:
            log.error(e)

    def send_stream_caption(self, caption:str):
        try:
            self.call(requests.SendStreamCaption(caption=caption))
        except Exception as e:
            log.error(e)


    ## Recording
    def start_record(self) -> None:
        try:
            return self.call(requests.StartRecord())
        except Exception as e:
            log.error(e)

    def pause_record(self):
        try:
            return self.call(requests.PauseRecord())
        except Exception as e:
            log.error(e)

    def resume_record(self):
        try:
            return self.call(requests.ResumeRecord())
        except Exception as e:
            log.error(e)

    def stop_recording(self) -> None:
        """
        outputPath: str -> The path to the saved recording
        """
        try:
            return self.call(requests.StopRecord())
        except Exception as e:
            log.error(e)

    def get_record_status(self):
        """
        outputActive: bool -> Whether recording is active
        outputPaused: bool -> Whether recording is paused
        outputTimecode: str -> The current timecode of the recording
        outputDuration: int -> The duration of the recording in milliseconds
        outputBytes: int -> The number of bytes written to the recording
        """
        try:
            return self.call(requests.GetRecordStatus())
        except Exception as e:
            log.error(e)

    def toggle_record(self):
        try:
            return self.call(requests.ToggleRecord())
        except Exception as e:
            log.error(e)

    def toggle_record_pause(self):
        try:
            return self.call(requests.ToggleRecordPause())
        except Exception as e:
            log.error(e)


    ## Replay Buffer
    def get_replay_buffer_status(self):
        """
        outputActive: bool -> Whether replay buffer is active
        """
        try:
            request = self.call(requests.GetReplayBufferStatus())

            if not request or not request.datain:
                log.warning("Replay buffer is not enabled in OBS!")
                return
            else:
                return request
        except Exception as e:
            log.error(e)

    def start_replay_buffer(self):
        try:
            return self.call(requests.StartReplayBuffer())
        except Exception as e:
            log.error(e)

    def stop_replay_buffer(self):
        try:
            return self.call(requests.StopReplayBuffer())
        except Exception as e:
            log.error(e)

    def save_replay_buffer(self):
        try:
            return self.call(requests.SaveReplayBuffer())
        except Exception as e:
            log.error(e)


    ## Virtual Camera
    def get_virtual_camera_status(self):
        """
        outputActive: bool -> Whether replay buffer is active
        """
        try:
            request = self.call(requests.GetVirtualCamStatus())

            if not request or not request.datain:
                log.warning("Virtual camera is not enabled in OBS!")
                return
            else:
                return request
        except Exception as e:
            log.error(e)

    def start_virtual_camera(self):
        try:
            return self.call(requests.StartVirtualCam())
        except Exception as e:
            log.error(e)

    def stop_virtual_camera(self):
        try:
            return self.call(requests.StopVirtualCam())
        except Exception as e:
            log.error(e)

    ## Studio Mode
    def get_studio_mode_enabled(self):
        """
        studioModeEnabled: bool -> Whether studio mode is enabled
        """
        try:
            return self.call(requests.GetStudioModeEnabled())
        except Exception as e:
            log.error(e)

    def set_studio_mode_enabled(self, enabled:bool):
        try:
            return self.call(requests.SetStudioModeEnabled(studioModeEnabled=enabled))
        except Exception as e:
            log.error(e)

    def trigger_transition(self):
        try:
            return self.call(requests.TriggerStudioModeTransition())
        except Exception as e:
            log.error(e)


    ## Input mixer
    def get_inputs(self) -> list:
        try:
            inputs = self.call(requests.GetInputList()).getInputs()
            return [input["inputName"] for input in inputs]
        except Exception as e:
            log.error(e)

    def get_input_muted(self, input: str) -> None:
        """
        inputMuted: bool -> Whether the input is muted
        """
        try:
            request = self.call(requests.GetInputMute(inputName=input))

            if not request or not request.datain:
                log.warning("Cannot find the input!")
                return
            else:
                return request
        except Exception as e:
            log.error(e)

    def set_input_muted(self, input: str, muted: bool) -> None:
        try:
            self.call(requests.SetInputMute(inputName=input, inputMuted=muted))
        except Exception as e:
            log.error(e)

    def get_input_volume(self, input: str):
        try:
            request = self.call(requests.GetInputVolume(inputName=input))

            if not request or not request.datain:
                log.warning("Cannot find the input!")
                return
            else:
                return request
        except Exception as e:
            log.error(e)

    def set_input_volume(self, input: str, volume: int) -> None:
        try:
            self.call(requests.SetInputVolume(inputName=input, inputVolumeDb=volume))
        except Exception as e:
            log.error(e)


    ## Scene Items
    def get_scene_items(self, sceneName: str) -> list:
        try:
            sceneItems = self.call(requests.GetSceneItemList(sceneName=sceneName)).getSceneItems()
            return [sceneItem["sourceName"] for sceneItem in sceneItems]
        except Exception as e:
            log.error(e)

    def get_scene_item_enabled(self, sceneName: str, sourceName: str) -> None:
        """
        sceneItemEnabled: bool -> Whether the scene item is enabled. true for enabled, false for disabled
        """
        try:
            sceneItemId = self.call(requests.GetSceneItemId(sceneName=sceneName, sourceName=sourceName)).getSceneItemId()
            return self.call(requests.GetSceneItemEnabled(sceneName=sceneName, sceneItemId=sceneItemId))
        except Exception as e:
            if str(e) == "'sceneItemId'":
                log.warning("Cannot find the scene item!")
            else:
                log.error(e)

    def set_scene_item_enabled(self, sceneName: str, sourceName: str, enabled: bool) -> None:
        try:
            sceneItemId = self.call(requests.GetSceneItemId(sceneName=sceneName, sourceName=sourceName)).getSceneItemId()
            self.call(requests.SetSceneItemEnabled(sceneName=sceneName, sceneItemId=sceneItemId, sceneItemEnabled=enabled))
        except Exception as e:
            log.error(e)


    ## Scenes
    def get_scenes(self) -> list:
        try:
            scenes = self.call(requests.GetSceneList()).getScenes()
            return [scene["sceneName"] for scene in scenes]
        except Exception as e:
            log.error(e)

    def get_current_program_scene(self) -> str:
        try:
            request = self.call(requests.GetCurrentProgramScene())
            return request.datain.get("currentProgramSceneName")
        except Exception as e:
            log.error(e)

    ## Credit for Studio Mode Preview fix: Rinma (https://github.com/Rinma)
    def switch_to_scene(self, scene:str) -> None:
        studioModeStatus = self.get_studio_mode_enabled()
        if studioModeStatus and studioModeStatus.datain and studioModeStatus.datain.get("studioModeEnabled"):
            try:
                self.call(requests.SetCurrentPreviewScene(sceneName=scene))
            except Exception as e:
                log.error(e)
        else:
            try:
                self.call(requests.SetCurrentProgramScene(sceneName=scene))
            except Exception as e:
                log.error(e)

    ## Scene Collections
    def get_scene_collections(self) -> list:
        try:
            sceneCollections = self.call(requests.GetSceneCollectionList()).getSceneCollections()
            return sceneCollections
        except Exception as e:
            log.error(e)

    def set_current_scene_collection(self, sceneCollectionName: str) -> None:
        try:
            self.call(requests.SetCurrentSceneCollection(sceneCollectionName=sceneCollectionName))
        except Exception as e:
            log.error(e)

    def get_source_filters(self, sourceName: str) -> list:
        try:
            source_filters = self.call(requests.GetSourceFilterList(sourceName=sourceName)).getfilters()
            return source_filters
        except Exception as e:
            log.error(e)

    def set_source_filter_enabled(self, sourceName: str, filterName: str, enabled: bool) -> None:
        try:
            self.call(requests.SetSourceFilterEnabled(sourceName=sourceName, filterName=filterName, filterEnabled=enabled))
        except Exception as e:
            log.error(e)

    def get_source_filter(self, sourceName: str, filterName: str) -> None:
        try:
            request = self.call(requests.GetSourceFilter(sourceName=sourceName, filterName=filterName))
            return request.datain if request else None
        except Exception as e:
            log.error(e)

    def get_stats(self):
        try:
            return self.call(requests.GetStats())
        except Exception as e:
            log.error(e)

    def get_video_settings(self):
        try:
            return self.call(requests.GetVideoSettings())
        except Exception as e:
            log.error(e)
