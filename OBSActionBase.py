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


class OBSActionBase(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.has_configuration = True
        self.custom_icon_entries = {}
        self.validated_custom_icons = {}
        self.custom_icon_cache_initialized = False

        self.status_label = Gtk.Label(
            label=self.plugin_base.lm.get("actions.base.status.no-connection"), css_classes=["bold", "red"]
        )

        self.update_custom_icon_cache()

        if not self.plugin_base.backend.get_connected():
            self.reconnect_obs()

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
        self.ip_entry = Adw.EntryRow(title=self.plugin_base.lm.get("actions.base.ip.label"))
        self.port_spinner = Adw.SpinRow.new_with_range(0, 65535, 1)
        self.port_spinner.set_title(self.plugin_base.lm.get("actions.base.port.label"))
        self.password_entry = Adw.PasswordEntryRow(title=self.plugin_base.lm.get("actions.base.password.label"))

        self.load_config_defaults()

        # Connect signals
        self.ip_entry.connect("notify::text", self.on_change_ip)
        self.port_spinner.connect("notify::value", self.on_change_port)
        self.password_entry.connect("notify::text", self.on_change_password)

        rows = [self.ip_entry, self.port_spinner, self.password_entry]

        # Add custom icon rows
        custom_icons = CLASS_ICON_MAP.get(self.__class__.__name__, [])
        for default_filename, label_text in custom_icons:
            entry = Adw.EntryRow(title=label_text)
            current_val = self.get_settings().get(f"custom_icon_{default_filename}", "")
            entry.set_text(current_val)
            
            # Create choose button
            btn = Gtk.Button.new_from_icon_name("document-open-symbolic")
            btn.connect("clicked", lambda button, df=default_filename: self.on_select_custom_icon(df))
            entry.add_suffix(btn)
            
            # Connect text change signal
            entry.connect("notify::text", lambda widget, pspec, df=default_filename: self.on_change_custom_icon_path(df))
            
            self.custom_icon_entries[default_filename] = entry
            rows.append(entry)

        return rows

    def on_select_custom_icon(self, default_filename):
        current_val = self.get_settings().get(f"custom_icon_{default_filename}", "")

        def on_select_callback(path):
            if not path:
                return
            # Update the text entry
            if default_filename in self.custom_icon_entries:
                self.custom_icon_entries[default_filename].set_text(path)
            # Save setting
            settings = self.get_settings()
            if settings.get(f"custom_icon_{default_filename}") != path:
                settings[f"custom_icon_{default_filename}"] = path
                self.set_settings(settings)
                self.update_custom_icon_cache()
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

    def on_change_custom_icon_path(self, default_filename):
        if default_filename not in self.custom_icon_entries:
            return
        path = self.custom_icon_entries[default_filename].get_text().strip()
        settings = self.get_settings()
        # Save setting only if changed to avoid loop
        if settings.get(f"custom_icon_{default_filename}") != path:
            settings[f"custom_icon_{default_filename}"] = path
            self.set_settings(settings)
            self.update_custom_icon_cache()
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
        super().set_media(media_path=media_path, *args, **kwargs)

    def load_config_defaults(self):
        settings = self.plugin_base.get_settings()
        ip = settings.setdefault("ip", "localhost")
        port = settings.setdefault("port", 4455)
        password = settings.setdefault("password", "")

        # Update ui
        self.ip_entry.set_text(ip)
        self.port_spinner.set_value(port)
        self.password_entry.set_text(password)
        self.update_ip_warning_status()
        self.update_status_label()

    def on_change_ip(self, entry, *args):
        settings = self.plugin_base.get_settings()
        settings["ip"] = self.ip_entry.get_text().strip()
        self.plugin_base.set_settings(settings)

        self.update_ip_warning_status()
        self.reconnect_obs()

    def update_ip_warning_status(self):
        valid = self.plugin_base.backend.OBSController.validate_ip(self.ip_entry.get_text().strip())
        if valid:
            self.ip_entry.remove_css_class("error")
        else:
            self.ip_entry.add_css_class("error")

    def on_change_port(self, spinner, *args):
        settings = self.plugin_base.get_settings()
        settings["port"] = int(spinner.get_value())
        self.plugin_base.set_settings(settings)

        self.reconnect_obs()

    def on_change_password(self, entry, *args):
        settings = self.plugin_base.get_settings()
        settings["password"] = entry.get_text()
        self.plugin_base.set_settings(settings)

        self.reconnect_obs()

    def reconnect_obs(self):
        threading.Thread(target=self._reconnect_obs, daemon=True, name="reconnect_obs").start()

    def _reconnect_obs(self):
        try:
            self.plugin_base.backend.connect_to(
                host=self.plugin_base.get_settings().get("ip", "localhost"),
                port=self.plugin_base.get_settings().get("port", 4455),
                password=self.plugin_base.get_settings().get("password") or "",
                timeout=3,
                legacy=False,
            )
        except Exception as e:
            log.error(e)

        if hasattr(self, "status_label"):
            self.update_status_label()

    def update_status_label(self) -> None:
        threading.Thread(target=self._update_status_label, daemon=True, name="update_status_label").start()

    def _update_status_label(self):
        if self.plugin_base.backend.get_connected():
            print("connected - label")
            self.status_label.set_label(self.plugin_base.lm.get("actions.base.status.connected"))
            self.status_label.remove_css_class("red")
            self.status_label.add_css_class("green")
        else:
            print("not connected - label")
            self.status_label.set_label(self.plugin_base.lm.get("actions.base.status.no-connection"))
            self.status_label.remove_css_class("green")
            self.status_label.add_css_class("red")

    def get_custom_config_area(self):
        self.update_status_label()
        return self.status_label
