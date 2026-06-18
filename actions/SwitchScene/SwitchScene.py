from plugins.com_core447_OBSPlugin.OBSActionBase import OBSActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase
from GtkHelper.GtkHelper import ComboRow

import os
import threading

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

class SwitchScene(OBSActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_state = -1
        
    def on_ready(self):
        self.current_state = -1
        # Connect to obs if not connected
        if self.plugin_base.backend is not None:
            if not self.plugin_base.get_connected():            # self.plugin_base.obs.connect_to(host="localhost", port=4444, timeout=3, legacy=False)
                self.reconnect_obs()

        # Show current scene status
        threading.Thread(target=self.show_current_scene_status, daemon=True, name="show_current_scene_status").start()

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
        if self.plugin_base.backend is None or not self.plugin_base.backend.get_connected():
            self.show_error()
            return
        scene_name = self.get_settings().get("scene")
        if scene_name in [None, ""]:
            return
        self.plugin_base.backend.switch_to_scene(scene_name)
        self.on_tick()

    def show_current_scene_status(self):
        if self.plugin_base.backend is None or not self.plugin_base.backend.get_connected():
            self.hide_error()
            self.show_for_state(0)
            return
        
        current_scene = self.plugin_base.backend.get_current_program_scene()
        configured_scene = self.get_settings().get("scene")

        if configured_scene in [None, ""] or current_scene is None:
            self.hide_error()
            self.show_for_state(0)
            return

        self.hide_error()
        if current_scene == configured_scene:
            self.show_for_state(1)
        else:
            self.show_for_state(0)

    def show_for_state(self, state: int):
        if state == self.current_state:
            return
        
        self.current_state = state
        image = "scene_inactive.png"
        if state == 1:
            image = "scene_active.png"

        self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", image), size=0.75)

    def on_tick(self):
        self.show_current_scene_status()

    def reconnect_obs(self):
        super().reconnect_obs()
        if hasattr(self, "scene_model"):
            self.load_scene_model()
            self.load_configs()