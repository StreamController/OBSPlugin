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

    def mark_disconnected(self):
        """Force the connection state to disconnected so the frontend retries the connection.

        The websocket library does not always report a closed OBS reliably (on_disconnect is
        not guaranteed to fire), so we additionally treat any missing/empty response as a lost
        connection. The frontend tick loop then reconnects on its own.
        """
        self.OBSController.connected = False

    def build_status_dict(self, status, key_mapping: dict) -> dict:
        """Build a response dict from an OBS request, mapping result keys to OBS response keys.

        Returns None (and marks the connection as lost) when the response is missing or its data
        is empty, which is what happens while OBS is closed. This both drives the reconnect and
        avoids a KeyError crashing the action tick.
        """
        if status is None:
            self.mark_disconnected()
            return None
        response_data = status.datain
        result = {}
        for result_key, obs_key in key_mapping.items():
            if obs_key not in response_data:
                self.mark_disconnected()
                return None
            result[result_key] = response_data[obs_key]
        return result

    def get_controller(self) -> OBSController:
        """
        Calling methods on the returned controller will raise a circular reference error from Pyro
        """
        return self.OBSController

    # Streaming
    def get_stream_status(self) -> dict:
        status = self.OBSController.get_stream_status()
        key_mapping = {
            "active": "outputActive",
            "reconnecting": "outputReconnecting",
            "timecode": "outputTimecode",
            "duration": "outputDuration",
            "congestion": "outputCongestion",
            "bytes": "outputBytes",
            "skipped_frames": "outputSkippedFrames",
            "total_frames": "outputTotalFrames"
        }
        return self.build_status_dict(status, key_mapping)

    def toggle_stream(self):
        status = self.OBSController.toggle_stream()
        if status is None:
            return False
        return status.datain["outputActive"]
    
    # Recording
    def get_record_status(self) -> dict:
        status = self.OBSController.get_record_status()
        key_mapping = {
            "active": "outputActive",
            "paused": "outputPaused",
            "timecode": "outputTimecode",
            "duration": "outputDuration",
            "bytes": "outputBytes"
        }
        return self.build_status_dict(status, key_mapping)

    def toggle_record(self):
        self.OBSController.toggle_record()

    def toggle_record_pause(self):
        self.OBSController.toggle_record_pause()

    # Replay Buffer
    def get_replay_buffer_status(self) -> dict:
        status = self.OBSController.get_replay_buffer_status()
        return self.build_status_dict(status, {"active": "outputActive"})

    def start_replay_buffer(self):
        self.OBSController.start_replay_buffer()

    def stop_replay_buffer(self):
        self.OBSController.stop_replay_buffer()

    def save_replay_buffer(self):
        self.OBSController.save_replay_buffer()

    # Virtual Camera
    def get_virtual_camera_status(self) -> dict:
        status = self.OBSController.get_virtual_camera_status()
        return self.build_status_dict(status, {"active": "outputActive"})

    def start_virtual_camera(self):
        self.OBSController.start_virtual_camera()

    def stop_virtual_camera(self):
        self.OBSController.stop_virtual_camera()

    # Studio Mode
    def get_studio_mode_enabled(self) -> dict:
        status = self.OBSController.get_studio_mode_enabled()
        return self.build_status_dict(status, {"active": "studioModeEnabled"})

    def set_studio_mode_enabled(self, enabled: bool):
        self.OBSController.set_studio_mode_enabled(enabled)

    def trigger_transition(self):
        self.OBSController.trigger_transition()

    # Input Mixing
    def get_inputs(self) -> list[str]:
        return self.OBSController.get_inputs()

    def get_input_muted(self, input: str):
        status = self.OBSController.get_input_muted(input)
        return self.build_status_dict(status, {"muted": "inputMuted"})

    def set_input_muted(self, input: str, muted: bool):
        self.OBSController.set_input_muted(input, muted)

    def get_input_volume(self, input: str):
        status = self.OBSController.get_input_volume(input)
        return self.build_status_dict(status, {"volume": "inputVolumeDb"})

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
        return self.build_status_dict(status, {"enabled": "sceneItemEnabled"})

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