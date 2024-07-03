import threading
from plugins.com_core447_OBSPlugin.OBSActionBase import OBSActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase
import os

class RecPlayPause(OBSActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_state = -1

    def on_ready(self):
        self.current_state = -1
        # Connect to obs if not connected
        if self.plugin_base.backend is not None:
            if not self.plugin_base.get_connected():
                # self.plugin_base.obs.connect_to(host="localhost", port=4444, timeout=3, legacy=False)
                self.reconnect_obs()

        # Show current rec status
        threading.Thread(target=self.show_current_rec_status, daemon=True, name="show_current_rec_status").start()

    def show_current_rec_status(self, new_paused = False):
        if not self.plugin_base.get_connected():
            self.show_error()
            return
        status = self.plugin_base.backend.get_record_status()
        if status is None:
            self.show_error()
            return
        if status["active"] and not status["paused"]:
            self.show_for_state(1)
        elif status["paused"]:
            self.show_for_state(2)
        else:
            self.show_for_state(0)

    def show_for_state(self, state: int):
        """
        0: Not Recording
        1: Recording
        2: Paused
        3: Stopping in progress
        """
        self.hide_error()
        if state == self.current_state:
            return
        self.current_state = state
        image = "record_inactive.png"
        if state == 1:
            self.set_bottom_label("Pause", font_size=16)
            image = "record_pause.png"
        if state == 2:
            self.set_bottom_label("Resume", font_size=16)
            image = "record_resume.png"
        else:
            self.set_bottom_label(None)

        self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", image))

    def on_key_down(self):
        if not self.plugin_base.backend.get_connected():
            return
        self.plugin_base.backend.toggle_record_pause()

    def on_tick(self):
        self.show_current_rec_status()