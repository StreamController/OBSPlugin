# from ...OBSActionBase import OBSActionBase
import threading
from plugins.com_core447_OBSPlugin.OBSActionBase import OBSActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

import os
class ToggleVirtualCamera(OBSActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_state = -1

    def on_ready(self):
        self.current_state = -1
        # Connect to obs if not connected
        if self.plugin_base.backend is not None:
            if not self.plugin_base.get_connected():            # self.plugin_base.obs.connect_to(host="localhost", port=4444, timeout=3, legacy=False)
                self.reconnect_obs()

        # Show current virtual camera status
        threading.Thread(target=self.show_current_virtual_camera_status, daemon=True, name="show_current_virtual_camera_status").start()

    def show_current_virtual_camera_status(self, new_paused = False):
        if self.plugin_base.backend is None:
            self.current_state = -1
            self.show_error()
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return
        if not self.plugin_base.backend.get_connected():
            self.current_state = -1
            self.show_error()
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return
        status = self.plugin_base.backend.get_virtual_camera_status()
        if status is None:
            self.current_state = -1
            self.show_error()
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return
        if status["active"]:
            self.show_for_state(1)
        else:
            self.show_for_state(0)

    def show_for_state(self, state: int):
        """
        0: Virtual Camera Turned Off
        1: Virtual Camera Turned On
        """
        if state == self.current_state:
            return
        
        self.current_state = state
        image = "virtual_camera_disabled.png"
        if state == 0:
            image = "virtual_camera_disabled.png"
        elif state == 1:
            image = "virtual_camera_enabled.png"

        self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", image), size=0.75)

    def on_key_down(self):
        if self.plugin_base.backend is None:
            self.current_state = -1
            self.show_error()
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return
        if not self.plugin_base.backend.get_connected():
            self.current_state = -1
            self.show_error()
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return
        if self.current_state == 0:
            self.plugin_base.backend.start_virtual_camera()
        else:
            self.plugin_base.backend.stop_virtual_camera()
        self.on_tick()

    def on_tick(self):
        self.show_current_virtual_camera_status()