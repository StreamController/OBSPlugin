from plugins.com_core447_OBSPlugin.OBSActionBase import OBSActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase
from GtkHelper.GtkHelper import ComboRow

import os

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

class SwitchScene(OBSActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def on_ready(self):
        # Connect to obs if not connected
        if self.plugin_base.backend is not None:
            if not self.plugin_base.get_connected():            # self.plugin_base.obs.connect_to(host="localhost", port=4444, timeout=3, legacy=False)
                self.reconnect_obs()

        media_path = os.path.join(self.plugin_base.PATH, "assets", "scene.png")
        self.set_media(media_path=media_path, size=0.75)

    def get_config_rows(self) -> list:
        super_rows = super().get_config_rows()

        self.scene_model = Gtk.StringList()
        self.scene_row = Adw.ComboRow(model=self.scene_model, title=self.plugin_base.lm.get("actions.switch.scene-row.label"))

        self.connect_signals()

        self.load_scene_model()
        self.load_configs()

        super_rows.append(self.scene_row)
        return super_rows
    
    def connect_signals(self):
        self.scene_row.connect("notify::selected", self.on_change_scene)

    def disconnect_signals(self):
        try:
            self.scene_row.disconnect_by_func(self.on_change_scene)
        except TypeError as e:
            pass

    def load_scene_model(self):
        self.disconnect_signals()
        # Clear model
        while self.scene_model.get_n_items() > 0:
            self.scene_model.remove(0)

        # Load model
        if self.plugin_base.backend.get_connected():
            scenes = self.plugin_base.backend.get_scene_names()
            if scenes is None:
                return
            for scene in scenes:
                self.scene_model.append(scene)

        self.connect_signals()

    def load_configs(self):
        self.load_selected_device()

    def load_selected_device(self):
        self.disconnect_signals()
        settings = self.get_settings()
        for i, scene_name in enumerate(self.scene_model):
            if scene_name.get_string() == settings.get("scene"):
                self.scene_row.set_selected(i)
                self.connect_signals()
                return
            
        self.scene_row.set_selected(Gtk.INVALID_LIST_POSITION)
        self.connect_signals()

    def on_change_scene(self, *args):
        settings = self.get_settings()
        selected_index = self.scene_row.get_selected()
        settings["scene"] = self.scene_model[selected_index].get_string()
        self.set_settings(settings)

    def on_key_down(self):
        scene_name = self.get_settings().get("scene")
        if scene_name in [None, ""]:
            return
        self.plugin_base.backend.switch_to_scene(scene_name)

    def reconnect_obs(self):
        super().reconnect_obs()
        if hasattr(self, "scene_model"):
            self.load_scene_model()
            self.load_configs()