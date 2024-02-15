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

class OBSActionBase(ActionBase):
    def __init__(self, action_id: str, action_name: str,
                 deck_controller: "DeckController", page: Page, coords: str, plugin_base: PluginBase):
        super().__init__(action_id=action_id, action_name=action_name,
            deck_controller=deck_controller, page=page, coords=coords, plugin_base=plugin_base)

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
        settings["ip"] = entry.get_text()
        self.plugin_base.set_settings(settings)

        self.reconnect_obs()

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
        print("reconnecing obs")
        self.plugin_base.backend.connect_to(
            host=self.plugin_base.get_settings().get("ip"),
            port=self.plugin_base.get_settings().get("port"),
            password=self.plugin_base.get_settings().get("password"),
            timeout=3, legacy=False)

        if self.plugin_base.backend.get_connected():
            self.status_label.set_label(self.plugin_base.lm.get("actions.base.status.connected"))
            self.status_label.remove_css_class("red")
            self.status_label.add_css_class("green")
        else:
            self.status_label.set_label(self.plugin_base.lm.get("actions.base.status.no-connection"))
            self.status_label.remove_css_class("green")
            self.status_label.add_css_class("red")

    def get_custom_config_area(self):
        return self.status_label