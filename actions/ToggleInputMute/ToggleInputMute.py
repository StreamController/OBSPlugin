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

class ToggleInputMute(OBSActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_state = -1
        
    def on_ready(self):
        self.current_state = -1
        # Connect to obs if not connected
        if self.plugin_base.backend is not None:
            if not self.plugin_base.get_connected():            # self.plugin_base.obs.connect_to(host="localhost", port=4444, timeout=3, legacy=False)
                self.reconnect_obs()

        # Show current input mute status
        threading.Thread(target=self.show_current_input_mute_status, daemon=True, name="show_current_input_mute_status").start()

    def show_current_input_mute_status(self, new_paused = False):
        if self.plugin_base.backend is None:
            self.current_state = -1
            self.show_error()
            return
        if not self.plugin_base.backend.get_connected():
            self.current_state = -1
            self.show_error()
            return
        if not self.get_settings().get("input"):
            self.current_state = -1
            self.show_error()
            return

        status = self.plugin_base.backend.get_input_muted(self.get_settings().get("input"))
        if status is None:
            self.current_state = -1
            self.show_error()
            return
        if status["muted"]:
            self.show_for_state(1)
        else:
            self.show_for_state(0)

    def show_for_state(self, state: int):
        """
        0: Input unmuted
        1: Input muted
        """
        if state == self.current_state:
            return
        
        self.current_state = state
        image = "record_inactive.png"
        if state == 0:
            image = "record_inactive.png"
        elif state == 1:
            image = "record_active.png"

        self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", image))

    def get_config_rows(self) -> list:
        super_rows = super().get_config_rows()

        self.input_model = Gtk.StringList()
        self.input_row = Adw.ComboRow(model=self.input_model, title=self.plugin_base.lm.get("actions.toggle-input-mute-row.label"))

        self.connect_signals()

        self.load_input_model()
        self.load_configs()

        super_rows.append(self.input_row)
        return super_rows
    
    def connect_signals(self):
        self.input_row.connect("notify::selected", self.on_mute_input)

    def disconnect_signals(self):
        try:
            self.input_row.disconnect_by_func(self.on_mute_input)
        except TypeError as e:
            pass

    def load_input_model(self):
        self.disconnect_signals()
        # Clear model
        while self.input_model.get_n_items() > 0:
            self.input_model.remove(0)

        # Load model
        if self.plugin_base.backend.get_connected():
            inputs = self.plugin_base.backend.get_inputs()
            if inputs is None:
                return
            for input in inputs:
                self.input_model.append(input)

        self.connect_signals()

    def load_configs(self):
        self.load_selected_device()

    def load_selected_device(self):
        self.disconnect_signals()
        settings = self.get_settings()
        for i, input_name in enumerate(self.input_model):
            if input_name.get_string() == settings.get("input"):
                self.input_row.set_selected(i)
                self.connect_signals()
                return
            
        self.input_row.set_selected(Gtk.INVALID_LIST_POSITION)
        self.connect_signals()

    def on_mute_input(self, *args):
        settings = self.get_settings()
        selected_index = self.input_row.get_selected()
        settings["input"] = self.input_model[selected_index].get_string()
        self.set_settings(settings)

    def on_key_down(self):
        if self.plugin_base.backend is None:
            self.current_state = -1
            self.show_error()
            return
        if not self.plugin_base.backend.get_connected():
            self.current_state = -1
            self.show_error()
            return

        input_name = self.get_settings().get("input")
        if input_name in [None, ""]:
            return

        if self.current_state == 0:
            self.plugin_base.backend.set_input_muted(input_name, True)
        else:
            self.plugin_base.backend.set_input_muted(input_name, False)
        self.on_tick()

    def on_tick(self):
        self.show_current_input_mute_status()

    def reconnect_obs(self):
        super().reconnect_obs()
        if hasattr(self, "input_model"):
            self.load_input_model()
            self.load_configs()