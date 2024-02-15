from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.ActionHolder import ActionHolder

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk

import sys
import os
import threading
from datetime import timedelta
from loguru import logger as log

# Add plugin to sys.paths
sys.path.append(os.path.dirname(__file__))

from OBSActionBase import OBSActionBase

from actions.ToggleRecord.ToggleRecord import ToggleRecord
from actions.RecPlayPause.RecPlayPause import RecPlayPause

class OBS(PluginBase):
    def __init__(self):
        super().__init__()

        # Launch backend
        print("launch backend")
        self.launch_backend(os.path.join(self.PATH, "backend", "backend.py"), os.path.join(self.PATH, ".venv"))
        print("backend launched")

        self.lm = self.locale_manager
        self.lm.set_to_os_default()


        self.register(
            plugin_name=self.lm.get("plugin.name"),
            github_repo="https://github.com/Core447/OBSPlugin",
            plugin_version="0.1",
            app_version="0.1.1-alpha",
        )


        toggle_record_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleRecord,
            action_id="dev_core447_OBSPlugin::ToggleRecord",
            action_name=self.lm.get("actions.toggle-record.name")
        )
        self.add_action_holder(toggle_record_action_holder)

        rec_play_pause_action_holder = ActionHolder(
            plugin_base=self,
            action_base=RecPlayPause,
            action_id="dev_core447_OBSPlugin::RecPlayPause",
            action_name=self.lm.get("actions.rec-play-pause.name")
        )
        self.add_action_holder(rec_play_pause_action_holder)

        # Load custom css
        self.add_css_stylesheet(os.path.join(self.PATH, "style.css"))