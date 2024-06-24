# from ...OBSActionBase import OBSActionBase
import threading
from plugins.com_core447_OBSPlugin.OBSActionBase import OBSActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

import os
# from ...OBSActionBase import OBSActionBase
import threading
from plugins.com_core447_OBSPlugin.OBSActionBase import OBSActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

import os
class SaveReplayBuffer(OBSActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_ready(self):
        # Connect to obs if not connected
        if self.plugin_base.backend is not None:
            if not self.plugin_base.get_connected():            # self.plugin_base.obs.connect_to(host="localhost", port=4444, timeout=3, legacy=False)
                self.reconnect_obs()
        self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "replay_buffer_save.png"), size=0.85)

    def on_key_down(self):
        if self.plugin_base.backend is None:
            self.show_error()
            return
        if not self.plugin_base.backend.get_connected():
            self.show_error()
            return
        self.plugin_base.backend.save_replay_buffer()