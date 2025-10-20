from .MixinBase import MixinBase, State

# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


class SetMixinGtk:

    SELECTOR_MAPPING = [State.ENABLED, State.DISABLED]

    def __init__(self, set_mixin: "SetMixin"):
        self.set_mixin = set_mixin

        self.input_model = Gtk.StringList()
        self.input_row = Adw.ComboRow(
            model=self.input_model, title=set_mixin.plugin_base.lm.get("actions.mixins.set.label")
        )

        self.input_model.append(set_mixin.plugin_base.lm.get("actions.mixins.set.enable"))
        self.input_model.append(set_mixin.plugin_base.lm.get("actions.mixins.set.disable"))

        self.input_row.connect("notify::selected", self.on_select)

        current_idx = SetMixinGtk.SELECTOR_MAPPING.index(set_mixin.mode)
        self.input_row.set_selected(current_idx)

    def get_config_rows(self):
        return [self.input_row]

    def on_select(self, *args):
        idx = self.input_row.get_selected()
        self.set_mixin.mode = SetMixinGtk.SELECTOR_MAPPING[idx]


class SetMixin(MixinBase):
    @property
    def mode(self):
        try:
            return State[self.get_settings()["set_mode"]]
        except KeyError:
            return State.ENABLED

    @mode.setter
    def mode(self, val: State):
        settings = self.get_settings()
        settings["set_mode"] = val.name
        self.set_settings(settings)

    def next_state(self) -> State:
        return self.mode

    def mixin_config_rows(self) -> list:
        self._set_mixin_gtk = SetMixinGtk(self)

        return self._set_mixin_gtk.get_config_rows()
