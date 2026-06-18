import logging
LOG = logging.getLogger(__name__)
# Set the logger level to ERROR
LOG.setLevel(logging.ERROR)

# Otherwise the obswebsocket library will create a separate logger with a lower warning level spamming the console if OBS isn't running
logging.getLogger = lambda *args, **kwargs: LOG


from streamcontroller_plugin_tools import BackendBase

from OBSController import OBSController
from obswebsocket import events
import os
import threading
import time

class BackendCache:
    def __init__(self):
        self.data = {}
        
    def get(self, key, ttl=0.1):
        if key in self.data:
            val, timestamp = self.data[key]
            if time.time() - timestamp < ttl:
                return val
        return None
        
    def set(self, key, val):
        self.data[key] = (val, time.time())
        
    def clear(self, key=None):
        if key:
            self.data.pop(key, None)
        else:
            self.data.clear()

class Backend(BackendBase):
    def __init__(self):
        super().__init__()
        self.cache = BackendCache()
        self.OBSController = OBSController()
        self.OBSController.connect_to(
            host=self.frontend.get_settings().get("ip", "localhost"),
            port=self.frontend.get_settings().get("port", 4455),
            password=self.frontend.get_settings().get("password") or ""
        )

    """
    Wrapper methods around OBSController aiming to allow a communication
    between the frontend and the backend in default python data types
    """

    def get_connected(self) -> bool:
        return self.OBSController.connected

    def connect_to(self, *args, **kwargs):
        self.OBSController.connect_to(*args, **kwargs)

    def get_controller(self) -> OBSController:
        """
        Calling methods on the returned controller will raise a circular reference error from Pyro
        """
        return self.OBSController

    # Streaming
    def get_stream_status(self) -> dict:
        cached = self.cache.get("stream_status", ttl=0.1)
        if cached is not None:
            return cached
        status = self.OBSController.get_stream_status()
        if status is None:
            return
        res = {
            "active": status.datain["outputActive"],
            "reconnecting": status.datain["outputReconnecting"],
            "timecode": status.datain["outputTimecode"],
            "duration": status.datain["outputDuration"],
            "congestion": status.datain["outputCongestion"],
            "bytes": status.datain["outputBytes"],
            "skipped_frames": status.datain["outputSkippedFrames"],
            "total_frames": status.datain["outputTotalFrames"]
        }
        self.cache.set("stream_status", res)
        return res

    def toggle_stream(self):
        self.cache.clear("stream_status")
        status = self.OBSController.toggle_stream()
        if status is None:
            return False
        return status.datain["outputActive"]
    
    # Recording
    def get_record_status(self) -> dict:
        cached = self.cache.get("record_status", ttl=0.1)
        if cached is not None:
            return cached
        status = self.OBSController.get_record_status()
        if status is None:
            return
        res = {
            "active": status.datain["outputActive"],
            "paused": status.datain["outputPaused"],
            "timecode": status.datain["outputTimecode"],
            "duration": status.datain["outputDuration"],
            "bytes": status.datain["outputBytes"]
        }
        self.cache.set("record_status", res)
        return res

    def toggle_record(self):
        self.cache.clear("record_status")
        self.OBSController.toggle_record()

    def toggle_record_pause(self):
        self.cache.clear("record_status")
        self.OBSController.toggle_record_pause()

    # Replay Buffer
    def get_replay_buffer_status(self) -> dict:
        cached = self.cache.get("replay_buffer_status", ttl=0.1)
        if cached is not None:
            return cached
        status = self.OBSController.get_replay_buffer_status()
        if status is None:
            return
        res = {
            "active": status.datain["outputActive"]
        }
        self.cache.set("replay_buffer_status", res)
        return res

    def start_replay_buffer(self):
        self.cache.clear("replay_buffer_status")
        self.OBSController.start_replay_buffer()

    def stop_replay_buffer(self):
        self.cache.clear("replay_buffer_status")
        self.OBSController.stop_replay_buffer()

    def save_replay_buffer(self):
        self.OBSController.save_replay_buffer()

    # Virtual Camera
    def get_virtual_camera_status(self) -> dict:
        cached = self.cache.get("virtual_camera_status", ttl=0.1)
        if cached is not None:
            return cached
        status = self.OBSController.get_virtual_camera_status()
        if status is None:
            return
        res = {
            "active": status.datain["outputActive"]
        }
        self.cache.set("virtual_camera_status", res)
        return res

    def start_virtual_camera(self):
        self.cache.clear("virtual_camera_status")
        self.OBSController.start_virtual_camera()

    def stop_virtual_camera(self):
        self.cache.clear("virtual_camera_status")
        self.OBSController.stop_virtual_camera()

    # Studio Mode
    def get_studio_mode_enabled(self) -> dict:
        cached = self.cache.get("studio_mode_enabled", ttl=0.1)
        if cached is not None:
            return cached
        status = self.OBSController.get_studio_mode_enabled()
        if status is None:
            return
        res = {
            "active": status.datain["studioModeEnabled"]
        }
        self.cache.set("studio_mode_enabled", res)
        return res

    def set_studio_mode_enabled(self, enabled: bool):
        self.cache.clear("studio_mode_enabled")
        self.OBSController.set_studio_mode_enabled(enabled)

    def trigger_transition(self):
        self.OBSController.trigger_transition()

    # Input Mixing
    def get_inputs(self) -> list[str]:
        cached = self.cache.get("inputs", ttl=2.0)
        if cached is not None:
            return cached
        res = self.OBSController.get_inputs()
        self.cache.set("inputs", res)
        return res

    def get_input_muted(self, input: str):
        key = f"input_muted_{input}"
        cached = self.cache.get(key, ttl=0.1)
        if cached is not None:
            return cached
        status = self.OBSController.get_input_muted(input)
        if status is None:
            return
        res = {
            "muted": status.datain["inputMuted"]
        }
        self.cache.set(key, res)
        return res

    def set_input_muted(self, input: str, muted: bool):
        key = f"input_muted_{input}"
        self.cache.clear(key)
        self.OBSController.set_input_muted(input, muted)

    def get_input_volume(self, input: str):
        status = self.OBSController.get_input_volume(input)
        if status is None:
            return
        return {
            "volume": status.datain["inputVolumeDb"]
        }

    def set_input_volume(self, input: str, volume: int):
        self.OBSController.set_input_volume(input, volume)

    # Scenes
    def get_scene_names(self) -> list[str]:
        cached = self.cache.get("scene_names", ttl=2.0)
        if cached is not None:
            return cached
        res = self.OBSController.get_scenes()
        self.cache.set("scene_names", res)
        return res
    
    def switch_to_scene(self, scene:str):
        self.cache.clear("current_program_scene")
        self.OBSController.switch_to_scene(scene)

    def get_current_program_scene(self) -> str:
        cached = self.cache.get("current_program_scene", ttl=0.1)
        if cached is not None:
            return cached
        res = self.OBSController.get_current_program_scene()
        self.cache.set("current_program_scene", res)
        return res

    # Scene Items
    def get_scene_items(self, sceneName: str) -> list[str]:
        return self.OBSController.get_scene_items(sceneName)

    def get_scene_item_enabled(self, sceneName: str, sourceName: str):
        key = f"scene_item_enabled_{sceneName}_{sourceName}"
        cached = self.cache.get(key, ttl=0.1)
        if cached is not None:
            return cached
        status = self.OBSController.get_scene_item_enabled(sceneName, sourceName)
        if status is None:
            return
        res = {
            "enabled": status.datain["sceneItemEnabled"]
        }
        self.cache.set(key, res)
        return res

    def set_scene_item_enabled(self, sceneName: str, sourceName: str, enabled: bool):
        key = f"scene_item_enabled_{sceneName}_{sourceName}"
        self.cache.clear(key)
        self.OBSController.set_scene_item_enabled(sceneName, sourceName, enabled)

    # Scene Collections
    def get_scene_collections(self) -> list[str]:
        return self.OBSController.get_scene_collections()

    def set_current_scene_collection(self, sceneCollectionName: str):
        return self.OBSController.set_current_scene_collection(sceneCollectionName)
    
    def get_source_filters(self, sourceName: str) -> list:
        return self.OBSController.get_source_filters(sourceName)
    
    def set_source_filter_enabled(self, sourceName: str, filterName: str, enabled: bool):
        self.OBSController.set_source_filter_enabled(sourceName, filterName, enabled)

    def get_source_filter(self, sourceName: str, filterName: str) -> None:
        return self.OBSController.get_source_filter(sourceName, filterName)
    
backend = Backend()