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

class Backend(BackendBase):
    def __init__(self):
        super().__init__()
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
        status = self.OBSController.get_stream_status()
        if status is None:
            return
        return {
            "active": status.datain["outputActive"],
            "reconnecting": status.datain["outputReconnecting"],
            "timecode": status.datain["outputTimecode"],
            "duration": status.datain["outputDuration"],
            "congestion": status.datain["outputCongestion"],
            "bytes": status.datain["outputBytes"],
            "skipped_frames": status.datain["outputSkippedFrames"],
            "total_frames": status.datain["outputTotalFrames"]
        }

    def toggle_stream(self):
        status = self.OBSController.toggle_stream()
        if status is None:
            return False
        return status.datain["outputActive"]
    
    # Recording
    def get_record_status(self) -> dict:
        status = self.OBSController.get_record_status()
        if status is None:
            return
        return {
            "active": status.datain["outputActive"],
            "paused": status.datain["outputPaused"],
            "timecode": status.datain["outputTimecode"],
            "duration": status.datain["outputDuration"],
            "bytes": status.datain["outputBytes"]
        }

    def toggle_record(self):
        self.OBSController.toggle_record()

    def toggle_record_pause(self):
        self.OBSController.toggle_record_pause()

    # Replay Buffer
    def get_replay_buffer_status(self) -> dict:
        status = self.OBSController.get_replay_buffer_status()
        if status is None:
            return
        return {
            "active": status.datain["outputActive"]
        }

    def start_replay_buffer(self):
        self.OBSController.start_replay_buffer()

    def stop_replay_buffer(self):
        self.OBSController.stop_replay_buffer()

    def save_replay_buffer(self):
        self.OBSController.save_replay_buffer()

    # Virtual Camera
    def get_virtual_camera_status(self) -> dict:
        status = self.OBSController.get_virtual_camera_status()
        if status is None:
            return
        return {
            "active": status.datain["outputActive"]
        }

    def start_virtual_camera(self):
        self.OBSController.start_virtual_camera()

    def stop_virtual_camera(self):
        self.OBSController.stop_virtual_camera()

    # Studio Mode
    def get_studio_mode_enabled(self) -> dict:
        status = self.OBSController.get_studio_mode_enabled()
        if status is None:
            return
        return {
            "active": status.datain["studioModeEnabled"]
        }

    def set_studio_mode_enabled(self, enabled: bool):
        self.OBSController.set_studio_mode_enabled(enabled)

    def trigger_transition(self):
        self.OBSController.trigger_transition()

    # Input Mixing
    def get_inputs(self) -> list[str]:
        return self.OBSController.get_inputs()

    def get_input_muted(self, input: str):
        status = self.OBSController.get_input_muted(input)
        if status is None:
            return
        return {
            "muted": status.datain["inputMuted"]
        }

    def set_input_muted(self, input: str, muted: bool):
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
        return self.OBSController.get_scenes()
    
    def switch_to_scene(self, scene:str):
        self.OBSController.switch_to_scene(scene)

    # Scene Items
    def get_scene_items(self, sceneName: str) -> list[str]:
        return self.OBSController.get_scene_items(sceneName)

    def get_scene_item_enabled(self, sceneName: str, sourceName: str):
        status = self.OBSController.get_scene_item_enabled(sceneName, sourceName)
        if status is None:
            return
        return {
            "enabled": status.datain["sceneItemEnabled"]
        }

    def set_scene_item_enabled(self, sceneName: str, sourceName: str, enabled: bool):
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