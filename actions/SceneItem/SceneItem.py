from OBSActionBase import OBSActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

from actions.mixins import State, MixinBase

from abc import ABC
import os
import threading

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


class SceneItemBase(OBSActionBase, MixinBase, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_state = State.UNKNOWN

        self.image_path_map = {
            State.UNKNOWN: os.path.join(self.plugin_base.PATH, "assets", "scene_item_disabled.png"),
            State.ENABLED: os.path.join(self.plugin_base.PATH, "assets", "scene_item_enabled.png"),
            State.DISABLED: os.path.join(self.plugin_base.PATH, "assets", "scene_item_disabled.png")
        }

    def on_ready(self):
        self.current_state = State.UNKNOWN
        # Connect to obs if not connected
        if self.backend is not None:
            if not self.plugin_base.get_connected():
                self.reconnect_obs()

        # Show current scene item status
        threading.Thread(target=self.show_current_scene_item_status, daemon=True, name="show_current_scene_item_status").start()

    # Copy-paste count: 1
    def set_media(self, *args, **kwargs):
        super().set_media(media_path=self.image_path_map.get(self.current_state), *args, **kwargs)

    def show_current_scene_item_status(self):
        if not self.plugin_base.get_connected():
            self.current_state = State.UNKNOWN
            self.hide_error()
            self.set_media()
            return
        if not self.get_settings().get("item"):
            self.current_state = State.UNKNOWN
            self.show_error()
            self.set_media()
            return

        status = self.backend.get_scene_item_enabled(self.get_settings().get("scene"), self.get_settings().get("item"))
        if status is None:
            self.current_state = State.UNKNOWN
            self.hide_error()
            self.set_media()
            return
        self.hide_error()
        if status["enabled"]:
            self.show_for_state(State.ENABLED)
        else:
            self.show_for_state(State.DISABLED)

    def show_for_state(self, state: State):
        if state == self.current_state:
            return

        self.current_state = state

        self.set_media(size=0.75)

    def get_config_rows(self) -> list:
        super_rows = super().get_config_rows()

        self.scene_model = Gtk.StringList()
        self.scene_row = Adw.ComboRow(model=self.scene_model, title=self.plugin_base.lm.get("actions.switch.scene-row.label"))

        self.item_model = Gtk.StringList()
        self.item_row = Adw.ComboRow(model=self.item_model, title=self.plugin_base.lm.get("actions.toggle-scene-item-enabled-row.label"))

        self.connect_signals()

        self.load_item_model()

        super_rows.append(self.scene_row)
        super_rows.append(self.item_row)
        return super_rows + self.mixin_config_rows()

    def connect_signals(self):
        self.scene_row.connect("notify::selected", self.on_scene_selected)
        self.item_row.connect("notify::selected", self.on_item_selected)

    def disconnect_signals(self):
        try:
            self.scene_row.disconnect_by_func(self.on_scene_selected)
            self.item_row.disconnect_by_func(self.on_item_selected)
        except TypeError:
            pass

    def load_item_model(self):
        self.disconnect_signals()
        while self.scene_model.get_n_items() > 0:
            self.scene_model.remove(0)
        while self.item_model.get_n_items() > 0:
            self.item_model.remove(0)

        self.scene_model.append("")
        self.item_model.append("")

        def fetch_and_populate():
            try:
                if self.backend.get_connected():
                    scenes = self.backend.get_scene_names()
                    if scenes is not None:
                        def populate():
                            self.disconnect_signals()
                            for scene in scenes:
                                self.scene_model.append(scene)
                            self.load_configs()
                            self.connect_signals()
                        GLib.idle_add(populate)
                        return
            except Exception as e:
                log.exception("Error in SceneItem load_item_model")
            def fallback():
                self.load_configs()
                self.connect_signals()
            GLib.idle_add(fallback)

        threading.Thread(target=fetch_and_populate, daemon=True, name="load_item_model").start()

    def load_items_for_scene(self, scene_name, on_done=None):
        self.disconnect_signals()
        while self.item_model.get_n_items() > 0:
            self.item_model.remove(0)

        self.item_model.append("")

        if not scene_name:
            if on_done:
                on_done()
            self.connect_signals()
            return

        def fetch_and_populate():
            try:
                if self.backend.get_connected():
                    items = self.backend.get_scene_items(scene_name)
                    if items is not None:
                        def populate():
                            self.disconnect_signals()
                            for item in items:
                                self.item_model.append(item)
                            if on_done:
                                on_done()
                            self.connect_signals()
                        GLib.idle_add(populate)
                        return
            except Exception as e:
                log.exception("Error in SceneItem load_items_for_scene")
            def fallback():
                if on_done:
                    on_done()
                self.connect_signals()
            GLib.idle_add(fallback)

        threading.Thread(target=fetch_and_populate, daemon=True, name="load_items_for_scene").start()

    def load_configs(self):
        self.load_selected_device()

    def load_selected_device(self):
        self.disconnect_signals()
        settings = self.get_settings()
        configured_scene = settings.get("scene")
        configured_item = settings.get("item")

        scene_found = False
        if configured_scene:
            for i, scene_name in enumerate(self.scene_model):
                if scene_name.get_string() == configured_scene:
                    self.scene_row.set_selected(i)
                    
                    def select_item():
                        self.disconnect_signals()
                        item_found = False
                        if configured_item:
                            for j, item_name in enumerate(self.item_model):
                                if item_name.get_string() == configured_item:
                                    self.item_row.set_selected(j)
                                    item_found = True
                                    break
                        if not item_found:
                            self.item_row.set_selected(0)
                        self.connect_signals()

                    self.load_items_for_scene(configured_scene, on_done=select_item)
                    scene_found = True
                    break
        
        if not scene_found:
            self.scene_row.set_selected(0)
            self.load_items_for_scene("", on_done=lambda: self.item_row.set_selected(0))

    def on_scene_selected(self, *args):
        settings = self.get_settings()
        selected_index_scene = self.scene_row.get_selected()
        if selected_index_scene == Gtk.INVALID_LIST_POSITION or selected_index_scene < 0 or selected_index_scene >= self.scene_model.get_n_items():
            scene_name = ""
        else:
            scene_name = self.scene_model[selected_index_scene].get_string()
        
        settings["scene"] = scene_name
        settings["item"] = ""
        self.set_settings(settings)
        
        self.disconnect_signals()
        self.load_items_for_scene(scene_name, on_done=lambda: self.item_row.set_selected(0))

    def on_item_selected(self, *args):
        settings = self.get_settings()
        selected_index_item = self.item_row.get_selected()
        if selected_index_item == Gtk.INVALID_LIST_POSITION or selected_index_item < 0 or selected_index_item >= self.item_model.get_n_items():
            settings["item"] = ""
        else:
            settings["item"] = self.item_model[selected_index_item].get_string()
        self.set_settings(settings)

    def on_key_down(self):
        if not self.plugin_base.get_connected():
            self.show_error()
            return

        scene_name = self.get_settings().get("scene")
        item_name = self.get_settings().get("item")
        if scene_name in [None, ""]:
            self.set_media()
            return
        if item_name in [None, ""]:
            self.set_media()
            return

        next_bool = bool(self.next_state().value)
        self.backend.set_scene_item_enabled(scene_name, item_name, next_bool)
        self.on_tick()

    def on_tick(self):
        self.show_current_scene_item_status()

    def on_connection_established(self):
        if hasattr(self, "scene_model") and hasattr(self, "item_model"):
            self.load_item_model()
