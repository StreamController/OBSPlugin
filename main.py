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
from actions.ToggleStream.ToggleStream import ToggleStream
from actions.RecPlayPause.RecPlayPause import RecPlayPause
from actions.SwitchScene.SwitchScene import SwitchScene

class OBS(PluginBase):
    def __init__(self):
        super().__init__()

        # Launch backend
        print("launch backend")
        self.launch_backend(os.path.join(self.PATH, "backend", "backend.py"), os.path.join(self.PATH, "backend", ".venv"), open_in_terminal=False)
        print("backend launched")

        self.lm = self.locale_manager
        self.lm.set_to_os_default()


        self.register(
            plugin_name=self.lm.get("plugin.name"),
            github_repo="https://github.com/StreamController/OBSPlugin",
            plugin_version="1.0.0",
            app_version="1.0.0-alpha",
        )

        toggle_record_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleRecord,
            action_id="com_core447_OBSPlugin::ToggleRecord",
            action_name=self.lm.get("actions.toggle-record.name")
        )
        self.add_action_holder(toggle_record_action_holder)

        toggle_stream_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleStream,
            action_id="com_core447_OBSPlugin::ToggleStream",
            action_name=self.lm.get("actions.toggle-stream.name")
        )
        self.add_action_holder(toggle_stream_action_holder)

        rec_play_pause_action_holder = ActionHolder(
            plugin_base=self,
            action_base=RecPlayPause,
            action_id="com_core447_OBSPlugin::RecPlayPause",
            action_name=self.lm.get("actions.rec-play-pause.name")
        )
        self.add_action_holder(rec_play_pause_action_holder)

        switch_scene_action_holder = ActionHolder(
            plugin_base=self,
            action_base=SwitchScene,
            action_id="com_core447_OBSPlugin::SwitchScene",
            action_name=self.lm.get("actions.switch-scene.name")
        )
        self.add_action_holder(switch_scene_action_holder)

        # Load custom css
        self.add_css_stylesheet(os.path.join(self.PATH, "style.css"))

    def get_connected(self):
        try:
            return self.backend.get_connected()
        except Exception as e:
            log.error(e)
            return False