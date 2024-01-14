from plugins.dev_core447_OBSPlugin.backend.OBSController import OBSController
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase

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
from obswebsocket import events

# Add plugin to sys.paths
sys.path.append(os.path.dirname(__file__))

from OBSActionBase import OBSActionBase

from actions.ToggleRecord.ToggleRecord import ToggleRecord
from actions.RecPlayPause.RecPlayPause import RecPlayPause

class OBS(PluginBase):
    def __init__(self):
        self.PLUGIN_NAME = "OBS"
        self.GITHUB_REPO = "https://github.com/your-github-repo"
        super().__init__()

        # Launch backend
        self.launch_backend(os.path.join(self.PATH, "backend", "backend.py"))

        self.add_action(ToggleRecord)
        self.add_action(RecPlayPause)

        # Load custom css
        self.add_css_stylesheet(os.path.join(self.PATH, "style.css"))