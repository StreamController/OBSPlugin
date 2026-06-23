import logging
LOG = logging.getLogger(__name__)
# Set the logger level to ERROR
LOG.setLevel(logging.ERROR)

# Otherwise the obswebsocket library will create a separate logger with a lower warning level spamming the console if OBS isn't running
logging.getLogger = lambda *args, **kwargs: LOG


from streamcontroller_plugin_tools import BackendBase

from OBSController import OBSController
import obswebsocket
from obswebsocket import events
import os
import threading
import time

class BackendCache:
    def __init__(self):
        self.data = {}
        self.lock = threading.Lock()
        
    def get(self, key, ttl=0.1):
        with self.lock:
            if key in self.data:
                val, timestamp = self.data[key]
                if time.time() - timestamp < ttl:
                    return val
            return None
        
    def set(self, key, val):
        with self.lock:
            self.data[key] = (val, time.time())
        
    def clear(self, key=None):
        with self.lock:
            if key:
                self.data.pop(key, None)
            else:
                self.data.clear()

class Backend(BackendBase):
    def __init__(self):
        super().__init__()
        self.cache = BackendCache()
        self.controllers = {}  # connection_id -> {"controller": OBSController, "config": config_dict}
        self._prev_stream_bytes = {}
        self._prev_stream_time = {}
        self.connecting_ids = set()
        self.connecting_lock = threading.Lock()
        
        # Initialize connections in background thread to avoid block
        threading.Thread(target=self.reload_connections, daemon=True, name="initial_connections_reload").start()
        self._start_reconnect_loop()

    def get_controller(self, connection_id="default") -> OBSController:
        if connection_id not in self.controllers:
            if not self.controllers:
                return None
            if "default" in self.controllers:
                return self.controllers["default"]["controller"]
            return list(self.controllers.values())[0]["controller"]
        return self.controllers[connection_id]["controller"]

    def reload_connections(self):
        try:
            settings = self.frontend.get_settings()
        except Exception as e:
            LOG.error(f"Could not retrieve settings from frontend: {e}")
            settings = {}

        connections = settings.get("connections", [])
        
        if not connections:
            ip = settings.get("ip", "localhost")
            port = settings.get("port", 4455)
            password = settings.get("password") or ""
            connections = [{
                "id": "default",
                "name": "Default",
                "ip": ip,
                "port": port,
                "password": password
            }]
            
        current_ids = set(c["id"] for c in connections)
        
        # Disconnect and delete removed connections
        for cid in list(self.controllers.keys()):
            if cid not in current_ids:
                LOG.info(f"Removing OBS connection profile: {cid}")
                try:
                    self.controllers[cid]["controller"].disconnect()
                    if self.controllers[cid]["controller"].event_obs is not None:
                        if self.controllers[cid]["controller"].event_obs.ws is not None:
                            self.controllers[cid]["controller"].event_obs.disconnect()
                except Exception as e:
                    LOG.error(e)
                del self.controllers[cid]
                
        # Connect or update existing connections
        for conn in connections:
            cid = conn["id"]
            ip = conn.get("ip", "localhost")
            try:
                port = int(conn.get("port", 4455))
            except ValueError:
                port = 4455
            password = conn.get("password", "")
            
            existing = self.controllers.get(cid)
            if existing:
                cfg = existing["config"]
                if cfg.get("ip") == ip and cfg.get("port") == port and cfg.get("password") == password:
                    if existing["controller"].connected:
                        continue
                        
            if existing:
                LOG.info(f"Config changed for profile {cid}, reconnecting...")
                try:
                    existing["controller"].disconnect()
                    if existing["controller"].event_obs is not None:
                        if existing["controller"].event_obs.ws is not None:
                            existing["controller"].event_obs.disconnect()
                except Exception as e:
                    LOG.error(e)
            else:
                LOG.info(f"Creating new controller for profile: {cid}")
                
            controller = OBSController()
            self.controllers[cid] = {
                "controller": controller,
                "config": {
                    "ip": ip,
                    "port": port,
                    "password": password
                }
            }
            threading.Thread(target=self._connect_profile, args=(cid, ip, port, password), daemon=True).start()

    def _connect_profile(self, cid, ip, port, password):
        with self.connecting_lock:
            if cid in self.connecting_ids:
                return
            self.connecting_ids.add(cid)
        try:
            if cid in self.controllers:
                controller = self.controllers[cid]["controller"]
                controller.connect_to(
                    host=ip,
                    port=port,
                    password=password,
                    timeout=3
                )
        except Exception as e:
            LOG.error(f"Error connecting profile {cid}: {e}")
        finally:
            with self.connecting_lock:
                self.connecting_ids.discard(cid)

    def _start_reconnect_loop(self):
        def loop():
            while True:
                time.sleep(10)
                try:
                    controllers_snapshot = list(self.controllers.items())
                except Exception:
                    continue
                for cid, info in controllers_snapshot:
                    controller = info["controller"]
                    if not controller.connected:
                        cfg = info["config"]
                        with self.connecting_lock:
                            is_connecting = cid in self.connecting_ids
                        if not is_connecting:
                            LOG.info(f"Auto-reconnecting profile {cid} to {cfg.get('ip')}:{cfg.get('port')}...")
                            threading.Thread(
                                target=self._connect_profile,
                                args=(cid, cfg.get("ip"), cfg.get("port"), cfg.get("password")),
                                daemon=True,
                                name=f"reconnect_{cid}"
                            ).start()
        threading.Thread(target=loop, daemon=True, name="obs_reconnect_loop").start()

    def test_connection(self, host, port, password) -> dict:
        test_ctrl = OBSController()
        try:
            success = test_ctrl.connect_to(host=host, port=port, password=password, timeout=3)
            if success and test_ctrl.connected:
                version_info = "Connected"
                try:
                    version_info = test_ctrl.call(obswebsocket.requests.GetVersion()).getObsVersion()
                except Exception:
                    pass
                return {"success": True, "version": version_info}
            else:
                return {"success": False, "error": "Could not connect"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            try:
                test_ctrl.disconnect()
            except Exception:
                pass
            if test_ctrl.event_obs is not None:
                try:
                    test_ctrl.event_obs.disconnect()
                except Exception:
                    pass

    """
    Wrapper methods around OBSController aiming to allow a communication
    between the frontend and the backend in default python data types
    """

    def get_connected(self, connection_id="default") -> bool:
        controller = self.get_controller(connection_id)
        return controller.connected if controller else False

    def connect_to(self, host=None, port=None, password=None, timeout=3, legacy=False, connection_id="default"):
        # Signature kept for backward compatibility; reload_connections should be preferred.
        controller = self.get_controller(connection_id)
        if controller:
            controller.connect_to(host=host, port=port, password=password, timeout=timeout, legacy=legacy)

    def get_controller_object(self, connection_id="default") -> OBSController:
        return self.get_controller(connection_id)

    # Streaming
    def get_stream_status(self, connection_id="default") -> dict:
        cache_key = f"stream_status_{connection_id}"
        cached = self.cache.get(cache_key, ttl=0.1)
        if cached is not None:
            return cached
            
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return None
            
        status = controller.get_stream_status()
        if status is None or not getattr(status, "status", False):
            return None
            
        res = {
            "active": status.datain.get("outputActive", False),
            "reconnecting": status.datain.get("outputReconnecting", False),
            "timecode": status.datain.get("outputTimecode", ""),
            "duration": status.datain.get("outputDuration", 0),
            "congestion": status.datain.get("outputCongestion", 0.0),
            "bytes": status.datain.get("outputBytes", 0),
            "skipped_frames": status.datain.get("outputSkippedFrames", 0),
            "total_frames": status.datain.get("outputTotalFrames", 0)
        }
        self.cache.set(cache_key, res)
        return res

    def toggle_stream(self, connection_id="default"):
        cache_key = f"stream_status_{connection_id}"
        self.cache.clear(cache_key)
        
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return False
            
        status = controller.toggle_stream()
        if status is None or not getattr(status, "status", False):
            return False
        return status.datain.get("outputActive", False)
    
    # Recording
    def get_record_status(self, connection_id="default") -> dict:
        cache_key = f"record_status_{connection_id}"
        cached = self.cache.get(cache_key, ttl=0.1)
        if cached is not None:
            return cached
            
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return None
            
        status = controller.get_record_status()
        if status is None or not getattr(status, "status", False):
            return None
            
        res = {
            "active": status.datain.get("outputActive", False),
            "paused": status.datain.get("outputPaused", False),
            "timecode": status.datain.get("outputTimecode", ""),
            "duration": status.datain.get("outputDuration", 0),
            "bytes": status.datain.get("outputBytes", 0)
        }
        self.cache.set(cache_key, res)
        return res

    def toggle_record(self, connection_id="default"):
        cache_key = f"record_status_{connection_id}"
        self.cache.clear(cache_key)
        controller = self.get_controller(connection_id)
        if controller and controller.connected:
            controller.toggle_record()

    def toggle_record_pause(self, connection_id="default"):
        cache_key = f"record_status_{connection_id}"
        self.cache.clear(cache_key)
        controller = self.get_controller(connection_id)
        if controller and controller.connected:
            controller.toggle_record_pause()

    # Replay Buffer
    def get_replay_buffer_status(self, connection_id="default") -> dict:
        cache_key = f"replay_buffer_status_{connection_id}"
        cached = self.cache.get(cache_key, ttl=0.1)
        if cached is not None:
            return cached
            
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return None
            
        status = controller.get_replay_buffer_status()
        if status is None or not getattr(status, "status", False):
            return None
            
        res = {
            "active": status.datain.get("outputActive", False)
        }
        self.cache.set(cache_key, res)
        return res

    def start_replay_buffer(self, connection_id="default"):
        cache_key = f"replay_buffer_status_{connection_id}"
        self.cache.clear(cache_key)
        controller = self.get_controller(connection_id)
        if controller and controller.connected:
            controller.start_replay_buffer()

    def stop_replay_buffer(self, connection_id="default"):
        cache_key = f"replay_buffer_status_{connection_id}"
        self.cache.clear(cache_key)
        controller = self.get_controller(connection_id)
        if controller and controller.connected:
            controller.stop_replay_buffer()

    def save_replay_buffer(self, connection_id="default"):
        controller = self.get_controller(connection_id)
        if controller and controller.connected:
            controller.save_replay_buffer()

    # Virtual Camera
    def get_virtual_camera_status(self, connection_id="default") -> dict:
        cache_key = f"virtual_camera_status_{connection_id}"
        cached = self.cache.get(cache_key, ttl=0.1)
        if cached is not None:
            return cached
            
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return None
            
        status = controller.get_virtual_camera_status()
        if status is None or not getattr(status, "status", False):
            return None
            
        res = {
            "active": status.datain.get("outputActive", False)
        }
        self.cache.set(cache_key, res)
        return res

    def start_virtual_camera(self, connection_id="default"):
        cache_key = f"virtual_camera_status_{connection_id}"
        self.cache.clear(cache_key)
        controller = self.get_controller(connection_id)
        if controller and controller.connected:
            controller.start_virtual_camera()

    def stop_virtual_camera(self, connection_id="default"):
        cache_key = f"virtual_camera_status_{connection_id}"
        self.cache.clear(cache_key)
        controller = self.get_controller(connection_id)
        if controller and controller.connected:
            controller.stop_virtual_camera()

    # Studio Mode
    def get_studio_mode_enabled(self, connection_id="default") -> dict:
        cache_key = f"studio_mode_enabled_{connection_id}"
        cached = self.cache.get(cache_key, ttl=0.1)
        if cached is not None:
            return cached
            
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return None
            
        status = controller.get_studio_mode_enabled()
        if status is None or not getattr(status, "status", False):
            return None
            
        res = {
            "active": status.datain.get("studioModeEnabled", False)
        }
        self.cache.set(cache_key, res)
        return res

    def set_studio_mode_enabled(self, enabled: bool, connection_id="default"):
        cache_key = f"studio_mode_enabled_{connection_id}"
        self.cache.clear(cache_key)
        controller = self.get_controller(connection_id)
        if controller and controller.connected:
            controller.set_studio_mode_enabled(enabled)

    def trigger_transition(self, connection_id="default"):
        controller = self.get_controller(connection_id)
        if controller and controller.connected:
            controller.trigger_transition()

    # Input Mixing
    def get_inputs(self, connection_id="default") -> list[str]:
        cache_key = f"inputs_{connection_id}"
        cached = self.cache.get(cache_key, ttl=2.0)
        if cached is not None:
            return cached
            
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return []
            
        res = controller.get_inputs()
        self.cache.set(cache_key, res)
        return res

    def get_input_muted(self, input: str, connection_id="default"):
        cache_key = f"input_muted_{input}_{connection_id}"
        cached = self.cache.get(cache_key, ttl=0.1)
        if cached is not None:
            return cached
            
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return None
            
        status = controller.get_input_muted(input)
        if status is None or not getattr(status, "status", False):
            return None
            
        res = {
            "muted": status.datain.get("inputMuted", False)
        }
        self.cache.set(cache_key, res)
        return res

    def set_input_muted(self, input: str, muted: bool, connection_id="default"):
        cache_key = f"input_muted_{input}_{connection_id}"
        self.cache.clear(cache_key)
        controller = self.get_controller(connection_id)
        if controller and controller.connected:
            controller.set_input_muted(input, muted)

    def get_input_volume(self, input: str, connection_id="default"):
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return None
            
        status = controller.get_input_volume(input)
        if status is None or not getattr(status, "status", False):
            return None
        return {
            "volume": status.datain.get("inputVolumeDb", 0.0)
        }

    def set_input_volume(self, input: str, volume: int, connection_id="default"):
        controller = self.get_controller(connection_id)
        if controller and controller.connected:
            controller.set_input_volume(input, volume)

    # Scenes
    def get_scene_names(self, connection_id="default") -> list[str]:
        cache_key = f"scene_names_{connection_id}"
        cached = self.cache.get(cache_key, ttl=2.0)
        if cached is not None:
            return cached
            
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return []
            
        res = controller.get_scenes()
        self.cache.set(cache_key, res)
        return res
    
    def switch_to_scene(self, scene: str, connection_id="default"):
        cache_key = f"current_program_scene_{connection_id}"
        self.cache.clear(cache_key)
        controller = self.get_controller(connection_id)
        if controller and controller.connected:
            controller.switch_to_scene(scene)

    def get_current_program_scene(self, connection_id="default") -> str:
        cache_key = f"current_program_scene_{connection_id}"
        cached = self.cache.get(cache_key, ttl=0.1)
        if cached is not None:
            return cached
            
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return None
            
        res = controller.get_current_program_scene()
        self.cache.set(cache_key, res)
        return res

    # Scene Items
    def get_scene_items(self, sceneName: str, connection_id="default") -> list[str]:
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return []
        return controller.get_scene_items(sceneName)

    def get_scene_item_enabled(self, sceneName: str, sourceName: str, connection_id="default"):
        cache_key = f"scene_item_enabled_{sceneName}_{sourceName}_{connection_id}"
        cached = self.cache.get(cache_key, ttl=0.1)
        if cached is not None:
            return cached
            
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return None
            
        status = controller.get_scene_item_enabled(sceneName, sourceName)
        if status is None or not getattr(status, "status", False):
            return None
            
        res = {
            "enabled": status.datain.get("sceneItemEnabled", False)
        }
        self.cache.set(cache_key, res)
        return res

    def set_scene_item_enabled(self, sceneName: str, sourceName: str, enabled: bool, connection_id="default"):
        cache_key = f"scene_item_enabled_{sceneName}_{sourceName}_{connection_id}"
        self.cache.clear(cache_key)
        controller = self.get_controller(connection_id)
        if controller and controller.connected:
            controller.set_scene_item_enabled(sceneName, sourceName, enabled)

    # Scene Collections
    def get_scene_collections(self, connection_id="default") -> list[str]:
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return []
        return controller.get_scene_collections()

    def set_current_scene_collection(self, sceneCollectionName: str, connection_id="default"):
        controller = self.get_controller(connection_id)
        if controller and controller.connected:
            return controller.set_current_scene_collection(sceneCollectionName)
    
    def get_source_filters(self, sourceName: str, connection_id="default") -> list:
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return []
        return controller.get_source_filters(sourceName)
    
    def set_source_filter_enabled(self, sourceName: str, filterName: str, enabled: bool, connection_id="default"):
        controller = self.get_controller(connection_id)
        if controller and controller.connected:
            controller.set_source_filter_enabled(sourceName, filterName, enabled)

    def get_source_filter(self, sourceName: str, filterName: str, connection_id="default") -> None:
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return None
        return controller.get_source_filter(sourceName, filterName)
    
    # Stats
    def get_stats(self, connection_id="default") -> dict:
        cache_key = f"stats_{connection_id}"
        cached = self.cache.get(cache_key, ttl=0.5)
        if cached is not None:
            return cached
            
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return None
            
        status = controller.get_stats()
        if status is None or not getattr(status, "status", False):
            return None
            
        res = {
            "cpu_usage": status.datain.get("cpuUsage", 0.0),
            "fps": status.datain.get("activeFps", 0.0),
            "memory_usage": status.datain.get("memoryUsage", 0.0)
        }
        self.cache.set(cache_key, res)
        return res

    def get_video_settings(self, connection_id="default") -> dict:
        cache_key = f"video_settings_{connection_id}"
        cached = self.cache.get(cache_key, ttl=10.0)
        if cached is not None:
            return cached
            
        controller = self.get_controller(connection_id)
        if not controller or not controller.connected:
            return None
            
        status = controller.get_video_settings()
        if status is None or not getattr(status, "status", False):
            return None
            
        res = {
            "fps_numerator": status.datain.get("fpsNumerator", 60),
            "fps_denominator": status.datain.get("fpsDenominator", 1)
        }
        self.cache.set(cache_key, res)
        return res

    def get_obs_stats(self, connection_id="default") -> dict:
        stats = self.get_stats(connection_id=connection_id)
        stream_status = self.get_stream_status(connection_id=connection_id)
        video_settings = self.get_video_settings(connection_id=connection_id)
        
        target_fps = 60
        if video_settings:
            num = video_settings.get("fps_numerator", 60)
            den = video_settings.get("fps_denominator", 1)
            if den > 0:
                target_fps = int(round(num / den))
        
        bandwidth = 0.0
        if stream_status and stream_status.get("active"):
            current_bytes = stream_status.get("bytes", 0)
            current_time = time.time()
            
            prev_bytes = self._prev_stream_bytes.get(connection_id, 0)
            prev_time = self._prev_stream_time.get(connection_id, 0.0)
            
            if prev_time > 0.0 and current_bytes >= prev_bytes:
                time_diff = current_time - prev_time
                if time_diff > 0.05:
                    bandwidth = ((current_bytes - prev_bytes) * 8.0) / (time_diff * 1000.0)
            
            self._prev_stream_bytes[connection_id] = current_bytes
            self._prev_stream_time[connection_id] = current_time
        else:
            self._prev_stream_bytes[connection_id] = 0
            self._prev_stream_time[connection_id] = 0.0
            
        res = {
            "cpu_usage": stats.get("cpu_usage", 0.0) if stats else 0.0,
            "fps": stats.get("fps", 0.0) if stats else 0.0,
            "target_fps": target_fps,
            "streaming": stream_status.get("active", False) if stream_status else False,
            "reconnecting": stream_status.get("reconnecting", False) if stream_status else False,
            "bandwidth": bandwidth
        }
        return res
    
backend = Backend()