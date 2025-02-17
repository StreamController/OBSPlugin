from abc import ABC

from plugins.com_core447_OBSPlugin.OBSActionBase import OBSActionBase
from plugins.com_core447_OBSPlugin.actions.mixins import MixinBase, State

import os
import threading

# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


class NotConnectedError(ValueError):
    pass


class InputNotFoundError(ValueError):
    pass


class InputMuteBase(OBSActionBase, MixinBase, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_state = State.UNKNOWN

        self.image_path_map = {
            State.UNKNOWN: os.path.join(self.plugin_base.PATH, "assets", "error.png"),
            State.ENABLED: os.path.join(self.plugin_base.PATH, "assets", "input_unmuted.png"),
            State.DISABLED: os.path.join(self.plugin_base.PATH, "assets", "input_muted.png"),
        }

    @property
    def input(self):
        return self.get_settings().get("input")

    @input.setter
    def input(self, val):
        settings = self.get_settings()
        settings["input"] = val
        self.set_settings(settings)

    def on_ready(self):
        self.current_state = State.UNKNOWN
        # Connect to obs if not connected
        if self.plugin_base.backend is not None:
            if not self.plugin_base.get_connected():
                self.reconnect_obs()

        # Show current input mute status
        threading.Thread(
            target=self.show_current_input_mute_status, daemon=True, name="show_current_input_mute_status"
        ).start()

    def set_media(self, *args, **kwargs):
        super().set_media(media_path=self.image_path_map.get(self.current_state), *args, **kwargs)

    def show_current_input_mute_status(self):
        if not self.plugin_base.get_connected():
            self.current_state = State.UNKNOWN
            self.show_error()
            self.set_media()
            return
        if not self.input:
            self.current_state = State.UNKNOWN
            self.show_error()
            self.set_media()
            return

        status = self.plugin_base.backend.get_input_muted(self.input)
        if status is None:
            self.current_state = State.UNKNOWN
            self.show_error()
            self.set_media()
            return
        if status["muted"]:
            self.show_for_state(State.DISABLED)
        else:
            self.show_for_state(State.ENABLED)

    def show_for_state(self, state: State):
        """
        State.DISABLED: Input unmuted
        State.ENABLED: Input muted
        """
        if state == self.current_state:
            return

        self.current_state = state
        self.set_media(size=0.9)

    def get_config_rows(self) -> list:
        super_rows = super().get_config_rows()

        self.input_model = Gtk.StringList()
        self.input_row = Adw.ComboRow(
            model=self.input_model, title=self.plugin_base.lm.get("actions.toggle-input-mute-row.label")
        )

        self.connect_signals()

        self.load_input_model()
        self.load_configs()

        super_rows.append(self.input_row)
        return super_rows + self.mixin_config_rows()

    def connect_signals(self):
        self.input_row.connect("notify::selected", self.on_mute_input)

    def disconnect_signals(self):
        try:
            self.input_row.disconnect_by_func(self.on_mute_input)
        except TypeError:
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
                self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
                return
            for input in inputs:
                self.input_model.append(input)

        self.connect_signals()

    def load_configs(self):
        self.load_selected_device()

    def load_selected_device(self):
        self.disconnect_signals()
        for i, input_name in enumerate(self.input_model):
            if input_name.get_string() == self.input:
                self.input_row.set_selected(i)
                self.connect_signals()
                return

        self.input_row.set_selected(Gtk.INVALID_LIST_POSITION)
        self.connect_signals()

    def on_mute_input(self, *args):
        selected_index = self.input_row.get_selected()
        self.input = self.input_model[selected_index].get_string()

    def assert_valid_state_for_update(self):
        if not self.plugin_base.get_connected():
            raise NotConnectedError()
        elif not self.input:
            raise InputNotFoundError()

        return

    def on_key_down(self):
        try:
            self.assert_valid_state_for_update()
        except NotConnectedError:
            self.current_state = State.UNKNOWN
            self.show_error()
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return
        except InputNotFoundError:
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return

        next_state = self.next_state()
        # API is inverse - set_disabled, not set_enabled
        self.plugin_base.backend.set_input_muted(self.input, not bool(next_state.value))
        self.on_tick()

    def on_tick(self):
        self.show_current_input_mute_status()

    def reconnect_obs(self):
        super().reconnect_obs()
        if hasattr(self, "input_model"):
            self.load_input_model()
            self.load_configs()
