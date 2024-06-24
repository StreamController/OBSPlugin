from obswebsocket import obsws, requests
import obswebsocket
from loguru import logger as log 
import websocket

class OBSController(obsws):
    def __init__(self):
        self.connected = False
        self.event_obs: obsws = None # All events are connected to this to avoid crash if a request is made in an event
        pass

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
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)

    def connect_to(self, host=None, port=None, timeout=1, legacy=False, **kwargs):
        try:
            log.debug(f"Trying to connect to obs with legacy: {legacy}")
            super().__init__(host=host, port=port, timeout=timeout, legacy=legacy, on_connect=self.on_connect, on_disconnect=self.on_disconnect, authreconnect=5, **kwargs)
            self.event_obs = obsws(host=host, port=port, timeout=timeout, legacy=legacy, on_connect=self.on_connect, on_disconnect=self.on_disconnect, authreconnect=5, **kwargs)
            self.connect()
            log.info("Successfully connected to OBS")
        except (obswebsocket.exceptions.ConnectionFailure, ValueError) as e:
            try:
                log.error(f"Failed to connect to OBS with legacy: {legacy}, trying with legacy: {not legacy}")
                super().__init__(host=host, port=port, timeout=timeout, legacy=not legacy, on_connect=self.on_connect, on_disconnect=self.on_disconnect, authreconnect=5, **kwargs)
                self.event_obs = obsws(host=host, port=port, timeout=timeout, legacy=not legacy, on_connect=self.on_connect, on_disconnect=self.on_disconnect, authreconnect=5, **kwargs)
                self.connect()
                log.info("Successfully connected to OBS")
            
            # ValueError: invalid port etc
            except (obswebsocket.exceptions.ConnectionFailure, ValueError) as e:
                log.error(f"Failed to connect to OBS: {e}")


    ## Streaming
    def start_stream(self) -> None:
        try:
            self.call(requests.StartStream())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)

    def stop_stream(self) -> None:
        try:
            self.call(requests.StopStream())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)

    def toggle_stream(self):
        """
        outputActive: bool -> The new state of the stream
        """
        try:
            self.call(requests.ToggleStream())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
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
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)
    
    def send_stream_caption(self, caption:str):
        try:
            self.call(requests.SendStreamCaption(caption=caption))
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)
    

    ## Recording
    def start_record(self) -> None:
        try:
            return self.call(requests.StartRecord())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)
    
    def pause_record(self):
        try:
            return self.call(requests.PauseRecord())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)
    
    def resume_record(self):
        try:
            return self.call(requests.ResumeRecord())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)

    def stop_recording(self) -> None:
        """
        outputPath: str -> The path to the saved recording
        """
        try:
            return self.call(requests.StopRecord())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
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
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)
    
    def toggle_record(self):
        try:
            return self.call(requests.ToggleRecord())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)
    
    def toggle_record_pause(self):
        try:
            return self.call(requests.ToggleRecordPause())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)
    
    
    ## Replay Buffer
    def start_replay_buffer(self):
        try:
            return self.call(requests.StartReplayBuffer())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)
    
    def stop_replay_buffer(self):
        try:
            return self.call(requests.StopReplayBuffer())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)

    def save_replay_buffer(self):
        try:
            return self.call(requests.SaveReplayBuffer())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)
    
    def get_replay_buffer_status(self):
        """
        outputActive: bool -> Whether replay buffer is active
        """
        try:
            return self.call(requests.GetReplayBufferStatus())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)


    ## Virtual Camera
    def start_virtual_camera(self):
        try:
            return self.call(requests.StartVirtualCam())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)
    
    def stop_virtual_camera(self):
        try:
            return self.call(requests.StopVirtualCam())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)
    
    def get_virtual_camera_status(self):
        """
        outputActive: bool -> Whether replay buffer is active
        """
        try:
            return self.call(requests.GetVirtualCamStatus())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)

    ## Studio Mode
    def get_studio_mode_enabled(self):
        """
        studioModeEnabled: bool -> Whether studio mode is enabled
        """
        try:
            return self.call(requests.GetStudioModeEnabled())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)
    
    def set_studio_mode_enabled(self, enabled:bool):
        return self.call(requests.SetStudioModeEnabled(studioModeEnabled=enabled))

    def trigger_transition(self):
        try:
            return self.call(requests.TriggerStudioModeTransition())
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)


    ## Input Muting
    def get_inputs(self) -> list:
        try:
            inputs = self.call(requests.GetInputList()).getInputs()
            return [input["inputName"] for input in inputs]
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)

    def get_input_muted(self, input: str) -> None:
        """
        inputMuted: bool -> Whether the input is muted
        """
        try:
            return self.call(requests.GetInputMute(inputName=input))
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)

    def set_input_muted(self, input: str, muted: bool) -> None:
        try:
            self.call(requests.SetInputMute(inputName=input, inputMuted=muted))
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)


    ## Scene Items
    def get_scene_items(self, sceneName: str) -> list:
        try:
            sceneItems = self.call(requests.GetSceneItemList(sceneName=sceneName)).getSceneItems()
            return [sceneItem["sourceName"] for sceneItem in sceneItems]
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)

    def get_scene_item_enabled(self, sceneName: str, sourceName: str) -> None:
        """
        sceneItemEnabled: bool -> Whether the scene item is enabled. true for enabled, false for disabled
        """
        try:
            sceneItemId = self.call(requests.GetSceneItemId(sceneName=sceneName, sourceName=sourceName)).getSceneItemId()
            return self.call(requests.GetSceneItemEnabled(sceneName=sceneName, sceneItemId=sceneItemId))
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            if str(e) == "'sceneItemId'":
                log.error("Cannot find the scene item!")
            else:
                log.error(e)

    def set_scene_item_enabled(self, sceneName: str, sourceName: str, enabled: bool) -> None:
        try:
            sceneItemId = self.call(requests.GetSceneItemId(sceneName=sceneName, sourceName=sourceName)).getSceneItemId()
            self.call(requests.SetSceneItemEnabled(sceneName=sceneName, sceneItemId=sceneItemId, sceneItemEnabled=enabled))
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)


    ## Scenes
    def get_scenes(self) -> list:
        try:
            scenes = self.call(requests.GetSceneList()).getScenes()
            return [scene["sceneName"] for scene in scenes]
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)
    
    def switch_to_scene(self, scene:str) -> None:
        try:
            self.call(requests.SetCurrentProgramScene(sceneName=scene))
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)

    
    ## Scene Collections
    def get_scene_collections(self) -> list:
        try:
            sceneCollections = self.call(requests.GetSceneCollectionList()).getSceneCollections()
            return sceneCollections
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)

    def set_current_scene_collection(self, sceneCollectionName: str) -> None:
        try:
            self.call(requests.SetCurrentSceneCollection(sceneCollectionName=sceneCollectionName))
        except (obswebsocket.exceptions.MessageTimeout,  websocket._exceptions.WebSocketConnectionClosedException, KeyError) as e:
            log.error(e)