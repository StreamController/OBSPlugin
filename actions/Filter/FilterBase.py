from plugins.com_core447_OBSPlugin.OBSActionBase import OBSActionBase
from plugins.com_core447_OBSPlugin.actions.mixins import State, MixinBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

from abc import ABC
import os
import threading

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


class FilterBase(OBSActionBase, MixinBase, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_state = State.UNKNOWN

    def on_ready(self):
        self.current_state = State.UNKNOWN
        # Connect to obs if not connected
        if self.plugin_base.backend is not None:
            if not self.plugin_base.get_connected():
                self.reconnect_obs()

        # Show current scene filter status
        threading.Thread(target=self.show_current_filter_status, daemon=True, name="show_current_filter_status").start()

    def show_current_filter_status(self):
        if not self.plugin_base.get_connected():
            self.current_state = State.UNKNOWN
            self.show_error()
            return
        if not self.get_settings().get("filter"):
            self.current_state = State.UNKNOWN
            self.show_error()
            return

        status = self.plugin_base.backend.get_source_filter(self.get_settings().get("scene"), self.get_settings().get("filter"))
        if status is None:
            self.current_state = State.UNKNOWN
            self.show_error()
            return
        if status["filterEnabled"]:
            self.show_for_state(State.ENABLED)
        else:
            self.show_for_state(State.DISABLED)

    def show_for_state(self, state: State):
        if state == self.current_state:
            return

        self.current_state = state
        image = "scene_item_disabled.png"

        if state == State.UNKNOWN:
            self.show_error()
        else:
            self.hide_error()

        if state == State.DISABLED:
            image = "scene_item_disabled.png"
        elif state == State.ENABLED:
            image = "scene_item_enabled.png"

        self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", image), size=0.75)

    def get_config_rows(self) -> list:
        super_rows = super().get_config_rows()

        self.scene_model = Gtk.StringList()
        self.scene_row = Adw.ComboRow(model=self.scene_model, title=self.plugin_base.lm.get("actions.switch.scene-row.label"))

        self.filter_model = Gtk.StringList()
        self.filter_row = Adw.ComboRow(model=self.filter_model, title=self.plugin_base.lm.get("actions.toggle-scene-filter-enabled-row.label"))

        self.connect_signals()

        self.load_filter_model()
        self.load_configs()

        super_rows.append(self.scene_row)
        super_rows.append(self.filter_row)
        return super_rows + self.mixin_config_rows()

    def connect_signals(self):
        self.scene_row.connect("notify::selected", self.on_scene_selected)
        self.filter_row.connect("notify::selected", self.on_filter_selected)

    def disconnect_signals(self):
        try:
            self.scene_row.disconnect_by_func(self.on_scene_selected)
            self.filter_row.disconnect_by_func(self.on_filter_selected)
        except TypeError:
            pass

    def load_filter_model(self):
        self.disconnect_signals()
        # Clear model
        while self.scene_model.get_n_items() > 0:
            self.scene_model.remove(0)
        while self.filter_model.get_n_items() > 0:
            self.filter_model.remove(0)

        # Load model
        if self.plugin_base.backend.get_connected():
            scenes = self.plugin_base.backend.get_scene_names()
            if scenes is None:
                return
            for scene in scenes:
                self.scene_model.append(scene)
            # Ensure selection is made if there's only one scene
            if len(scenes) == 1:
                self.get_settings()["scene"] = scenes[0]
                self.scene_row.set_selected(0)
                self.load_filters_for_scene(scenes[0])

        self.connect_signals()

    def load_filters_for_scene(self, scene_name):
        # Clear filters model
        while self.filter_model.get_n_items() > 0:
            self.filter_model.remove(0)

        if self.plugin_base.backend.get_connected():
            filters = self.plugin_base.backend.get_source_filters(scene_name)
            if filters is None:
                self.show_error()
                return
            for item in filters:
                self.filter_model.append(item.get("filterName"))
            # Ensure selection is made if there's only one item
            if len(filters) == 1:
                self.filter_row.set_selected(0)

    def load_configs(self):
        self.load_config_values()

    def load_config_values(self):
        self.disconnect_signals()
        settings = self.get_settings()
        for i, scene_name in enumerate(self.scene_model):
            if scene_name.get_string() == settings.get("scene"):
                self.scene_row.set_selected(i)
                self.load_filters_for_scene(scene_name.get_string())
                for j, item_name in enumerate(self.filter_model):
                    if item_name.get_string() == settings.get("filter"):
                        self.filter_row.set_selected(j)
                        break
                self.connect_signals()
                return

        self.scene_row.set_selected(Gtk.INVALID_LIST_POSITION)
        self.filter_row.set_selected(Gtk.INVALID_LIST_POSITION)
        self.connect_signals()

    def on_scene_selected(self, *args):
        settings = self.get_settings()
        selected_index_scene = self.scene_row.get_selected()
        if selected_index_scene != Gtk.INVALID_LIST_POSITION:
            scene_name = self.scene_model[selected_index_scene].get_string()
            settings["scene"] = scene_name
            self.set_settings(settings)
            self.load_filters_for_scene(scene_name)

    def on_filter_selected(self, *args):
        settings = self.get_settings()
        selected_index_item = self.filter_row.get_selected()
        if selected_index_item != Gtk.INVALID_LIST_POSITION:
            settings["filter"] = self.filter_model[selected_index_item].get_string()
            self.set_settings(settings)

    def on_key_down(self):
        if not self.plugin_base.get_connected():
            self.current_state = State.UNKNOWN
            self.show_error()
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return

        scene_name = self.get_settings().get("scene")
        filter_name = self.get_settings().get("filter")
        if scene_name in [None, ""]:
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return
        if filter_name in [None, ""]:
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return

        next_state = bool(self.next_state().value)
        self.plugin_base.backend.set_source_filter_enabled(scene_name, filter_name, next_state)
        self.on_tick()

    def on_tick(self):
        self.show_current_filter_status()

    def reconnect_obs(self):
        super().reconnect_obs()
        if hasattr(self, "scene_model") and hasattr(self, "filter_model"):
            self.load_filter_model()
            self.load_configs()
