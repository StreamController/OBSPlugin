from plugins.dev_core447_OBSPlugin.OBSActionBase import OBSActionBase
import os

class RecPlayPause(OBSActionBase):
    ACTION_NAME = "Recording Play/Pause"
    CONTROLS_KEY_IMAGE = True
    def __init__(self, deck_controller, page, coords):
        self.current_state = -1
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

    def on_ready(self):
        # Connect to obs if not connected
        if not self.PLUGIN_BASE.backend.get_connected():
            # self.PLUGIN_BASE.obs.connect_to(host="localhost", port=4444, timeout=3, legacy=False)
            self.reconnect_obs()

        # Show current rec status
        self.show_current_rec_status()

    def show_current_rec_status(self, new_paused = False):
        if not self.PLUGIN_BASE.backend.get_connected():
            self.set_key(media_path=os.path.join(self.PLUGIN_BASE.PATH, "assets", "error.png"))
            return
        status = self.PLUGIN_BASE.backend.get_record_status()
        if status is None:
            self.set_key(media_path=os.path.join(self.PLUGIN_BASE.PATH, "assets", "error.png"))
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

        self.set_key(media_path=os.path.join(self.PLUGIN_BASE.PATH, "assets", image))

    def on_key_down(self):
        if not self.PLUGIN_BASE.backend.get_connected():
            return
        self.PLUGIN_BASE.backend.toggle_record_pause()

    def on_tick(self):
        self.show_current_rec_status()