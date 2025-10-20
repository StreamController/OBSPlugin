from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page

# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

import threading
from loguru import logger as log


class OBSActionBase(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.has_configuration = True

        self.status_label = Gtk.Label(
            label=self.plugin_base.lm.get("actions.base.status.no-connection"), css_classes=["bold", "red"]
        )

        if not self.plugin_base.backend.get_connected():
            self.reconnect_obs()

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

        return [self.ip_entry, self.port_spinner, self.password_entry]

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
