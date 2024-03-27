from streamcontroller_plugin_tools import BackendBase

from OBSController import OBSController
from obswebsocket import events
import os
import threading
import Pyro5.api

@Pyro5.api.expose
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
    
    def get_connected(self) -> bool:
        return self.OBSController.connected
    
    def toggle_record(self):
        self.OBSController.toggle_record()

    def toggle_record_pause(self):
        self.OBSController.toggle_record_pause()

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