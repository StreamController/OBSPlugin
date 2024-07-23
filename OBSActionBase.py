from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

import threading
from loguru import logger as log

import socket
import ipaddress

class OBSActionBase(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.has_configuration = True

        self.status_label = Gtk.Label(label=self.plugin_base.lm.get("actions.base.status.no-connection"), css_classes=["bold", "red"])

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

        self.plugin_base.set_settings(settings)

    def on_change_ip(self, entry, *args):
        settings = self.plugin_base.get_settings()
        new_host = self.validate_ip(entry)
        if new_host:
            settings["ip"] = new_host
            self.plugin_base.set_settings(settings)
            self.reconnect_obs()

    def validate_ip(self, entry):
        new_host = entry.get_text()
        try:
            # validate that it resolves
            new_ip = socket.gethostbyname(new_host)
        except socket.gaierror as e:
            log.error("Unable to resolve host for OBS connection.")
            return None
        try:
            # see if the host is an IP already
            valid_ip = ipaddress.ip_address(new_host)
            # it is, so confirm it's as-typed
            if valid_ip.compressed != new_ip and valid_ip.exploded != new_ip:
                log.error("Resolved IP does not match input")
                return None # typed address does not match
        except ValueError as e:
            # handle edge case where socket resolves non-IPs to an IP starting with 0
            if new_ip.startswith('0'):
                log.error("IP does not appear valid.")
                return None
        log.info("IP is valid")
        return new_ip

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
                timeout=3, legacy=False)
        except Exception as e:
            log.error(e)
        
        self.update_status_label()
        
    def update_status_label(self) -> None:
        threading.Thread(target=self._update_status_label, daemon=True, name="update_status_label").start()

    def _update_status_label(self):
        if self.plugin_base.backend.get_connected():
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
