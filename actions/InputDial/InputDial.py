from plugins.com_core447_OBSPlugin.OBSActionBase import OBSActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.DeckManagement.InputIdentifier import Input, InputEvent
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase
from GtkHelper.GtkHelper import ComboRow

import os
import threading
import math

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

class InputDial(OBSActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.muted = None
        self.volume = None
        self.last_muted = None
        self.last_volume = None

    def on_ready(self):
        # Connect ot obs if not connected
        if self.plugin_base.backend is not None:
            if not self.plugin_base.get_connected():
                self.reconnect_obs()
        
        # Show current input volume
        self.muted = None
        self.volume = None
        threading.Thread(target=self.show_current_input_volume, daemon=True, name="show_current_input_volume").start()
    
    def show_current_input_volume(self):
        if self.plugin_base.backend is None:
            self.current_state = None
            self.show_error()
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return
        if not self.plugin_base.backend.get_connected():
            self.current_state = None
            self.show_error()
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return
        if not self.get_settings().get("input"):
            self.current_state = None
            self.show_error()
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return
        
        # update muted
        status = self.plugin_base.backend.get_input_muted(self.get_settings().get("input"))
        if status is None:
            self.current_state = -1
            self.show_error()
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return
        self.muted = status["muted"]

        # update volume
        status = self.plugin_base.backend.get_input_volume(self.get_settings().get("input"))
        if status is None:
            self.current_state = -1
            self.show_error()
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return
        self.volume = self.db_to_volume(status["volume"])

        # Now render the button
        image = "input_muted.png" if self.muted else "input_unmuted.png"
        label = f"{self.volume}%"

        if self.last_muted != self.muted:
            self.last_muted = self.muted
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", image), size=0.9)
        if self.last_volume != self.volume:
            self.last_volume = self.volume
            self.set_label(label)

    def get_config_rows(self) -> list:
        super_rows = super().get_config_rows()

        self.input_model = Gtk.StringList()
        self.input_row = Adw.ComboRow(model=self.input_model, title=self.plugin_base.lm.get("actions.input-dial-row.label"))

        self.connect_signals()

        self.load_input_model()
        self.load_configs()

        super_rows.append(self.input_row)
        return super_rows

    def connect_signals(self):
        self.input_row.connect("notify::selected", self.on_input_change)

    def disconnect_signals(self):
        try:
            self.input_row.disconnect_by_func(self.on_input_change)
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
                self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
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
    
    def on_input_change(self, *args):
        settings = self.get_settings()
        selected_index = self.input_row.get_selected()
        settings["input"] = self.input_model[selected_index].get_string()
        self.set_settings(settings)

    def event_callback(self, event: InputEvent, data: dict = None):
        if event == Input.Key.Events.DOWN or event == Input.Dial.Events.DOWN:
            self.mute_toggle()
        if str(event) == str(Input.Dial.Events.TURN_CW):
            self.volume_change(+5)
        if str(event) == str(Input.Dial.Events.TURN_CCW):
            self.volume_change(-5)

    def mute_toggle(self):
        if self.plugin_base.backend is None:
            self.current_state = None
            self.show_error()
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return
        if not self.plugin_base.backend.get_connected():
            self.current_state = None
            self.show_error()
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return

        input_name = self.get_settings().get("input")
        if input_name in [None, ""]:
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return

        self.muted = not self.muted
        self.plugin_base.backend.set_input_muted(input_name, self.muted)
        self.on_tick()
    
    def volume_change(self, diff):
        if self.plugin_base.backend is None:
            self.current_state = None
            self.show_error()
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return
        if not self.plugin_base.backend.get_connected():
            self.current_state = None
            self.show_error()
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return

        input_name = self.get_settings().get("input")
        if input_name in [None, ""]:
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "error.png"))
            return
        
        self.volume += diff
        if self.volume < 0:
            self.volume = 0
        if self.volume > 100:
            self.volume = 100
        self.plugin_base.backend.set_input_volume(input_name, self.volume_to_db(self.volume))
        self.on_tick()

    def on_tick(self):
        self.show_current_input_volume()

    def reconnect_obs(self):
        super().reconnect_obs()
        if hasattr(self, "input_model"):
            self.load_input_model()
            self.load_configs()
        self.muted = None
        self.volume = None
    
    def volume_to_db(self, vol):
        if vol == 0:
            return -100
        if vol > 100:
            return 0
        return math.log(vol/100)*10/math.log(1.5)

    def db_to_volume(self, db):
        if db < -100:
            return 0
        if db > 0:
            return 100
        return math.floor(1.5**(db/10) * 100)