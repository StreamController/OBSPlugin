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

class SwitchSceneCollection(OBSActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def on_ready(self):
        # Connect to obs if not connected
        if self.plugin_base.backend is not None:
            if not self.plugin_base.get_connected():            # self.plugin_base.obs.connect_to(host="localhost", port=4444, timeout=3, legacy=False)
                self.reconnect_obs()

        self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "scene.png"), size=0.75)

    def get_config_rows(self) -> list:
        super_rows = super().get_config_rows()

        self.scene_collection_model = Gtk.StringList()
        self.scene_collection_row = Adw.ComboRow(model=self.scene_collection_model, title=self.plugin_base.lm.get("actions.switch-scene-collection-row.label"))

        self.connect_signals()

        self.load_scene_collection_model()
        self.load_configs()

        super_rows.append(self.scene_collection_row)
        return super_rows
    
    def connect_signals(self):
        self.scene_collection_row.connect("notify::selected", self.on_change_scene_collection)

    def disconnect_signals(self):
        try:
            self.scene_collection_row.disconnect_by_func(self.on_change_scene_collection)
        except TypeError as e:
            pass

    def load_scene_collection_model(self):
        self.disconnect_signals()
        # Clear model
        while self.scene_collection_model.get_n_items() > 0:
            self.scene_collection_model.remove(0)

        # Load model
        if self.plugin_base.backend.get_connected():
            sceneCollections = self.plugin_base.backend.get_scene_collections()
            if sceneCollections is None:
                return
            for sceneCollection in sceneCollections:
                self.scene_collection_model.append(sceneCollection)

        self.connect_signals()

    def load_configs(self):
        self.load_selected_device()

    def load_selected_device(self):
        self.disconnect_signals()
        settings = self.get_settings()
        for i, scene_collection_name in enumerate(self.scene_collection_model):
            if scene_collection_name.get_string() == settings.get("scene_collection"):
                self.scene_collection_row.set_selected(i)
                self.connect_signals()
                return
            
        self.scene_collection_row.set_selected(Gtk.INVALID_LIST_POSITION)
        self.connect_signals()

    def on_change_scene_collection(self, *args):
        settings = self.get_settings()
        selected_index = self.scene_collection_row.get_selected()
        settings["scene_collection"] = self.scene_collection_model[selected_index].get_string()
        self.set_settings(settings)

    def on_key_down(self):
        scene_collection_name = self.get_settings().get("scene_collection")
        if scene_collection_name in [None, ""]:
            return
        self.plugin_base.backend.set_current_scene_collection(scene_collection_name)

    def reconnect_obs(self):
        super().reconnect_obs()
        if hasattr(self, "scene_collection_model"):
            self.load_scene_collection_model()
            self.load_configs()