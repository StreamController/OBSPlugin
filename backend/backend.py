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
            host=self.frontend.get_settings().get("ip"),
            port=self.frontend.get_settings().get("port"),
            password=self.frontend.get_settings().get("password")
        )

    """
    Wrapper methods around OBSController aiming to allow a communication
    between the frontend and the backend in default python data types
    """

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

    # Replay Buffer
    def get_replay_buffer_status(self) -> dict:
        status = self.OBSController.get_replay_buffer_status()
        if status is None:
            return
        return {
            "active": status.datain["outputActive"]
        }

    # Virtual Camera
    def get_virtual_camera_status(self) -> dict:
        status = self.OBSController.get_virtual_camera_status()
        if status is None:
            return
        return {
            "active": status.datain["outputActive"]
        }
    
    def get_connected(self) -> bool:
        return self.OBSController.connected

    def toggle_stream(self):
        status = self.OBSController.toggle_stream()
        if status is None:
            return False
        return status.datain["outputActive"]
    
    def toggle_record(self):
        self.OBSController.toggle_record()

    def toggle_record_pause(self):
        self.OBSController.toggle_record_pause()

    # Replay Buffer
    def start_replay_buffer(self):
        self.OBSController.start_replay_buffer()

    def stop_replay_buffer(self):
        self.OBSController.stop_replay_buffer()

    def save_replay_buffer(self):
        self.OBSController.save_replay_buffer()

    # Virtual Camera
    def start_virtual_camera(self):
        self.OBSController.start_virtual_camera()

    def stop_virtual_camera(self):
        self.OBSController.stop_virtual_camera()

    def connect_to(self, *args, **kwargs):
        self.OBSController.connect_to(*args, **kwargs)

    def get_controller(self) -> OBSController:
        """
        Calling methods on the returned controller will raise a circular reference error from Pyro
        """
        return self.OBSController
    
    def get_scene_names(self) -> list[str]:
        return self.OBSController.get_scenes()
    
    def switch_to_scene(self, scene:str):
        self.OBSController.switch_to_scene(scene)
    
backend = Backend()