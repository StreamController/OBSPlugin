from abc import ABC

from OBSActionBase import OBSActionBase
from actions.mixins import MixinBase, State

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
            State.UNKNOWN: os.path.join(self.plugin_base.PATH, "assets", "input_muted.png"),
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
        if self.backend is not None:
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
            self.hide_error()
            self.set_media()
            return
        if not self.input:
            self.current_state = State.UNKNOWN
            self.show_error()
            self.set_media()
            return

        status = self.backend.get_input_muted(self.input)
        if status is None:
            self.current_state = State.UNKNOWN
            self.hide_error()
            self.set_media()
            return
        self.hide_error()
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
        while self.input_model.get_n_items() > 0:
            self.input_model.remove(0)
        self.input_model.append("")

        def fetch_and_populate():
            try:
                if self.backend.get_connected():
                    inputs = self.backend.get_inputs()
                    if inputs is not None:
                        def populate():
                            self.disconnect_signals()
                            for input_name in inputs:
                                self.input_model.append(input_name)
                            self.load_configs()
                            self.connect_signals()
                        GLib.idle_add(populate)
                        return
            except Exception as e:
                log.exception("Error in InputMuteBase load_input_model")
            def fallback():
                self.load_configs()
                self.connect_signals()
            GLib.idle_add(fallback)

        threading.Thread(target=fetch_and_populate, daemon=True, name="load_input_model").start()

    def load_configs(self):
        self.load_selected_device()

    def load_selected_device(self):
        self.disconnect_signals()
        configured_input = self.input

        if not configured_input:
            self.input_row.set_selected(0)
            self.connect_signals()
            return

        for i, input_name in enumerate(self.input_model):
            if input_name.get_string() == configured_input:
                self.input_row.set_selected(i)
                self.connect_signals()
                return

        self.input_row.set_selected(0)
        self.connect_signals()

    def on_mute_input(self, *args):
        selected_index = self.input_row.get_selected()
        if selected_index == Gtk.INVALID_LIST_POSITION or selected_index < 0 or selected_index >= self.input_model.get_n_items():
            self.input = ""
        else:
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
            self.show_error()
            return
        except InputNotFoundError:
            self.show_error()
            return

        next_state = self.next_state()
        # API is inverse - set_disabled, not set_enabled
        self.backend.set_input_muted(self.input, not bool(next_state.value))
        self.on_tick()

    def on_tick(self):
        self.show_current_input_mute_status()

    def on_connection_established(self):
        if hasattr(self, "input_model"):
            self.load_input_model()
