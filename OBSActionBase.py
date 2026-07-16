from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page

# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib
import globals as gl

import threading
import os
import time
from loguru import logger as log

CLASS_ICON_MAP = {
    "ToggleStream": [
        ("stream_inactive.png", "Stream Off Icon"),
        ("stream_active.png", "Stream On Icon"),
        ("stream_reconnecting.png", "Stream Reconnecting Icon"),
    ],
    "ToggleRecord": [
        ("record_inactive.png", "Record Off Icon"),
        ("record_active.png", "Record On Icon"),
        ("record_resume.png", "Record Paused Icon"),
    ],
    "RecPlayPause": [
        ("record_inactive.png", "Record Off Icon"),
        ("record_pause.png", "Record Pause Button Icon"),
        ("record_resume.png", "Record Resume Button Icon"),
    ],
    "ToggleReplayBuffer": [
        ("replay_buffer_disabled.png", "Replay Buffer Off Icon"),
        ("replay_buffer_enabled.png", "Replay Buffer On Icon"),
    ],
    "SaveReplayBuffer": [
        ("replay_buffer_save.png", "Save Replay Buffer Icon"),
    ],
    "ToggleVirtualCamera": [
        ("virtual_camera_disabled.png", "Virtual Camera Off Icon"),
        ("virtual_camera_enabled.png", "Virtual Camera On Icon"),
    ],
    "ToggleStudioMode": [
        ("studio_mode_disabled.png", "Studio Mode Off Icon"),
        ("studio_mode_enabled.png", "Studio Mode On Icon"),
    ],
    "TriggerTransition": [
        ("transition.png", "Transition Icon"),
    ],
    "ToggleInputMute": [
        ("input_unmuted.png", "Input Unmuted Icon"),
        ("input_muted.png", "Input Muted Icon"),
    ],
    "SetInputMute": [
        ("input_unmuted.png", "Input Unmuted Icon"),
        ("input_muted.png", "Input Muted Icon"),
    ],
    "InputDial": [
        ("input_unmuted.png", "Input Unmuted Icon"),
        ("input_muted.png", "Input Muted Icon"),
    ],
    "ToggleSceneItemEnabled": [
        ("scene_item_enabled.png", "Scene Item Enabled Icon"),
        ("scene_item_disabled.png", "Scene Item Disabled Icon"),
    ],
    "SetSceneItemEnabled": [
        ("scene_item_enabled.png", "Scene Item Enabled Icon"),
        ("scene_item_disabled.png", "Scene Item Disabled Icon"),
    ],
    "ToggleFilter": [
        ("scene_item_enabled.png", "Filter Enabled Icon"),
        ("scene_item_disabled.png", "Filter Disabled Icon"),
    ],
    "SetFilter": [
        ("scene_item_enabled.png", "Filter Enabled Icon"),
        ("scene_item_disabled.png", "Filter Disabled Icon"),
    ],
    "SwitchScene": [
        ("scene_active.png", "Active Scene Icon"),
        ("scene_inactive.png", "Inactive Scene Icon"),
    ],
    "SwitchSceneCollection": [
        ("scene.png", "Switch Scene Collection Icon"),
    ],
    "OBSStats": [
        ("stats.png", "OBS Stats Icon"),
    ],
}


class BackendProxy:
    def __init__(self, plugin_base, action):
        self._plugin_base = plugin_base
        self._action = action

    def __getattr__(self, name):
        backend = self._plugin_base.backend
        if backend is None:
            if name == "get_connected":
                return lambda *args, **kwargs: False
            return lambda *args, **kwargs: None
            
        attr = getattr(backend, name)
        if callable(attr):
            def wrapper(*args, **kwargs):
                lock = getattr(self._plugin_base, "rpyc_lock", None)
                if lock is not None:
                    with lock:
                        return attr(*args, connection_id=self._action.connection_id, **kwargs)
                else:
                    return attr(*args, connection_id=self._action.connection_id, **kwargs)
            return wrapper
        return attr


class OBSActionBase(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.has_configuration = True
        self.custom_icon_entries = {}
        self.custom_icon_clear_buttons = {}
        self.validated_custom_icons = {}
        self.custom_icon_cache_initialized = False

        self.status_label = Gtk.Label(
            label=self.plugin_base.lm.get("actions.base.status.no-connection"), css_classes=["bold", "red"]
        )

        self.update_custom_icon_cache()

        if self.plugin_base.backend is not None:
            self.reconnect_obs()

    @property
    def connection_id(self):
        return self.get_settings().get("connection_id", "default")

    @property
    def backend(self):
        if not hasattr(self, "_backend_proxy"):
            self._backend_proxy = BackendProxy(self.plugin_base, self)
        return self._backend_proxy

    @backend.setter
    def backend(self, value):
        pass

    def update_custom_icon_cache(self):
        self.validated_custom_icons = {}
        settings = self.get_settings()
        custom_icons = CLASS_ICON_MAP.get(self.__class__.__name__, [])
        for default_filename, _ in custom_icons:
            path = settings.get(f"custom_icon_{default_filename}", "").strip()
            if path and os.path.isfile(path):
                self.validated_custom_icons[default_filename] = path

        if getattr(self, "on_ready_called", False):
            self.custom_icon_cache_initialized = True

    def get_config_rows(self) -> list:
        self.connection_model = Gtk.StringList()
        self.connection_row = Adw.ComboRow(
            model=self.connection_model,
            title="OBS Connection Profile"
        )

        self.load_config_defaults()

        # Connect signals
        self.connection_row.connect("notify::selected", self.on_change_connection)

        rows = [self.connection_row]

        # Add custom icon rows
        custom_icons = CLASS_ICON_MAP.get(self.__class__.__name__, [])
        for default_filename, label_text in custom_icons:
            entry = Adw.ActionRow(title=label_text)
            current_val = self.get_settings().get(f"custom_icon_{default_filename}", "")
            
            # Set subtitle to filename without extension
            if current_val:
                filename = os.path.basename(current_val)
                name_without_ext = os.path.splitext(filename)[0]
                entry.set_subtitle(name_without_ext)
            else:
                entry.set_subtitle("Default Icon")
            
            # Create choose button
            btn = Gtk.Button.new_from_icon_name("document-open-symbolic")
            btn.connect("clicked", lambda button, df=default_filename: self.on_select_custom_icon(df))
            entry.add_suffix(btn)
            
            # Create clear button
            clear_btn = Gtk.Button.new_from_icon_name("edit-clear-symbolic")
            clear_btn.set_sensitive(bool(current_val))
            clear_btn.connect("clicked", lambda button, df=default_filename: self.on_clear_custom_icon(df))
            entry.add_suffix(clear_btn)
            
            self.custom_icon_entries[default_filename] = entry
            self.custom_icon_clear_buttons[default_filename] = clear_btn
            rows.append(entry)

        return rows

    def on_select_custom_icon(self, default_filename):
        current_val = self.get_settings().get(f"custom_icon_{default_filename}", "")

        def on_select_callback(path):
            if not path:
                return
            # Save setting
            settings = self.get_settings()
            if settings.get(f"custom_icon_{default_filename}") != path:
                settings[f"custom_icon_{default_filename}"] = path
                self.set_settings(settings)
                self.update_custom_icon_cache()
                
                # Update subtitle
                if default_filename in self.custom_icon_entries:
                    filename = os.path.basename(path)
                    name_without_ext = os.path.splitext(filename)[0]
                    self.custom_icon_entries[default_filename].set_subtitle(name_without_ext)
                
                # Enable clear button
                if default_filename in self.custom_icon_clear_buttons:
                    self.custom_icon_clear_buttons[default_filename].set_sensitive(True)
                
                # Trigger update immediately
                if hasattr(self, "_current_state"):
                    self._current_state = None
                else:
                    self.current_state = None
                if hasattr(self, "on_tick"):
                    self.on_tick()
                elif hasattr(self, "on_ready"):
                    self.on_ready()

        GLib.idle_add(gl.app.let_user_select_asset, current_val, on_select_callback)

    def on_clear_custom_icon(self, default_filename):
        settings = self.get_settings()
        if settings.get(f"custom_icon_{default_filename}"):
            settings[f"custom_icon_{default_filename}"] = ""
            self.set_settings(settings)
            self.update_custom_icon_cache()
            
            if default_filename in self.custom_icon_entries:
                self.custom_icon_entries[default_filename].set_subtitle("Default Icon")
            if default_filename in self.custom_icon_clear_buttons:
                self.custom_icon_clear_buttons[default_filename].set_sensitive(False)
                
            # Trigger update immediately
            if hasattr(self, "_current_state"):
                self._current_state = None
            else:
                self.current_state = None
            if hasattr(self, "on_tick"):
                self.on_tick()
            elif hasattr(self, "on_ready"):
                self.on_ready()

    def set_media(self, media_path=None, *args, **kwargs):
        if not getattr(self, "custom_icon_cache_initialized", False) and getattr(self, "on_ready_called", False):
            self.update_custom_icon_cache()

        if media_path:
            filename = os.path.basename(media_path)
            if hasattr(self, "validated_custom_icons") and filename in self.validated_custom_icons:
                media_path = self.validated_custom_icons[filename]
        
        method = super().set_media
        GLib.idle_add(lambda: method(media_path=media_path, *args, **kwargs))

    def set_bottom_label(self, *args, **kwargs):
        method = super().set_bottom_label
        GLib.idle_add(lambda: method(*args, **kwargs))

    def set_top_label(self, *args, **kwargs):
        method = super().set_top_label
        GLib.idle_add(lambda: method(*args, **kwargs))

    def set_center_label(self, *args, **kwargs):
        method = super().set_center_label
        GLib.idle_add(lambda: method(*args, **kwargs))

    def set_background_color(self, *args, **kwargs):
        method = super().set_background_color
        GLib.idle_add(lambda: method(*args, **kwargs))

    def load_config_defaults(self):
        self.connections_list = self.plugin_base.get_settings().get("connections", [])
        
        while self.connection_model.get_n_items() > 0:
            self.connection_model.remove(0)
            
        selected_idx = 0
        active_id = self.connection_id
        
        for i, conn in enumerate(self.connections_list):
            self.connection_model.append(conn.get("name", "Unnamed"))
            if conn.get("id") == active_id:
                selected_idx = i
                
        self.connection_row.set_selected(selected_idx)
        self.update_status_label()

    def on_change_connection(self, combo, *args):
        selected_idx = combo.get_selected()
        if 0 <= selected_idx < len(self.connections_list):
            settings = self.get_settings()
            settings["connection_id"] = self.connections_list[selected_idx]["id"]
            self.set_settings(settings)
            
            self.reconnect_obs()
            self.on_connection_changed()

    def on_connection_changed(self):
        # Virtual method to be overridden by subclasses
        pass

    def reconnect_obs(self):
        threading.Thread(target=self._reconnect_obs, daemon=True, name="reconnect_obs").start()

    def _reconnect_obs(self):
        # Let backend process sync
        time.sleep(0.5)
        self.update_status_label()
        GLib.idle_add(self.on_connection_established)

    def on_connection_established(self):
        pass

    def update_status_label(self) -> None:
        if not hasattr(self, "status_label") or self.status_label is None:
            return
        def check():
            try:
                connected = self.backend.get_connected()
            except Exception:
                connected = False
            GLib.idle_add(self._update_status_label, connected)
        threading.Thread(target=check, daemon=True, name="update_status_label").start()

    def _update_status_label(self, connected):
        if not hasattr(self, "status_label") or self.status_label is None:
            return
        if connected:
            self.status_label.set_label(self.plugin_base.lm.get("actions.base.status.connected"))
            self.status_label.remove_css_class("red")
            self.status_label.add_css_class("green")
        else:
            self.status_label.set_label(self.plugin_base.lm.get("actions.base.status.no-connection"))
            self.status_label.remove_css_class("green")
            self.status_label.add_css_class("red")

    def get_custom_config_area(self):
        self.update_status_label()
        return self.status_label
