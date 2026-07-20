from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport

# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib

import sys
import os
import uuid
import threading
from loguru import logger as log

# Add plugin to sys.paths
plugin_dir = os.path.dirname(__file__)
if plugin_dir not in sys.path:
    sys.path.append(plugin_dir)

from .actions.ToggleStream.ToggleStream import ToggleStream

from .actions.ToggleRecord.ToggleRecord import ToggleRecord
from .actions.RecPlayPause.RecPlayPause import RecPlayPause

from .actions.ToggleReplayBuffer.ToggleReplayBuffer import ToggleReplayBuffer
from .actions.SaveReplayBuffer.SaveReplayBuffer import SaveReplayBuffer

from .actions.ToggleVirtualCamera.ToggleVirtualCamera import ToggleVirtualCamera

from .actions.ToggleStudioMode.ToggleStudioMode import ToggleStudioMode
from .actions.TriggerTransition.TriggerTransition import TriggerTransition

from .actions.InputMute import SetInputMute, ToggleInputMute
from .actions.InputDial.InputDial import InputDial

from .actions.SwitchScene.SwitchScene import SwitchScene
from .actions.SceneItem import SetSceneItemEnabled, ToggleSceneItemEnabled
from .actions.Filter import SetFilter, ToggleFilter
from .actions.SwitchSceneCollection.SwitchSceneCollection import SwitchSceneCollection
from .actions.OBSStats.OBSStats import OBSStats


class OBS(PluginBase):
    def __init__(self):
        super().__init__()

        self.rpyc_lock = threading.Lock()
        self.has_plugin_settings = True
        self.migrate_connection_settings()

        # Launch backend
        print("launch backend")
        self.launch_backend(
            os.path.join(self.PATH, "backend", "backend.py"),
            os.path.join(self.PATH, "backend", ".venv"),
            open_in_terminal=False,
        )
        print("backend launched")

        self.lm = self.locale_manager
        self.lm.set_to_os_default()

        self.register(
            plugin_name=self.lm.get("plugin.name"),
            github_repo="https://github.com/oparada1988/OBSPlugin",
            plugin_version="1.0.5",
            app_version="1.0.0-alpha",
        )

        # Streaming
        toggle_stream_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleStream,
            action_id_suffix="ToggleStream",
            action_name=self.lm.get("actions.toggle-stream.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNTESTED,
            },
        )
        self.add_action_holder(toggle_stream_action_holder)

        # Recording
        toggle_record_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleRecord,
            action_id_suffix="ToggleRecord",
            action_name=self.lm.get("actions.toggle-record.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNTESTED,
            },
        )
        self.add_action_holder(toggle_record_action_holder)

        rec_play_pause_action_holder = ActionHolder(
            plugin_base=self,
            action_base=RecPlayPause,
            action_id_suffix="RecPlayPause",
            action_name=self.lm.get("actions.rec-play-pause.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNTESTED,
            },
        )
        self.add_action_holder(rec_play_pause_action_holder)

        # Replay Buffer
        toggle_replay_buffer_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleReplayBuffer,
            action_id_suffix="ToggleReplayBuffer",
            action_name=self.lm.get("actions.toggle-replay-buffer.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            },
        )
        self.add_action_holder(toggle_replay_buffer_action_holder)

        save_replay_buffer_action_holder = ActionHolder(
            plugin_base=self,
            action_base=SaveReplayBuffer,
            action_id_suffix="SaveReplayBuffer",
            action_name=self.lm.get("actions.save-replay-buffer.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            },
        )
        self.add_action_holder(save_replay_buffer_action_holder)

        # Virtual Camera
        toggle_virtual_camera_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleVirtualCamera,
            action_id_suffix="ToggleVirtualCamera",
            action_name=self.lm.get("actions.toggle-virtual-camera.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            },
        )
        self.add_action_holder(toggle_virtual_camera_action_holder)

        # Studio Mode
        toggle_studio_mode_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleStudioMode,
            action_id_suffix="ToggleStudioMode",
            action_name=self.lm.get("actions.toggle-studio-mode.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            },
        )
        self.add_action_holder(toggle_studio_mode_action_holder)

        trigger_transition_action_holder = ActionHolder(
            plugin_base=self,
            action_base=TriggerTransition,
            action_id_suffix="TriggerTransition",
            action_name=self.lm.get("actions.trigger-transition.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            },
        )
        self.add_action_holder(trigger_transition_action_holder)

        # Input mixing
        toggle_input_mute_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleInputMute,
            action_id_suffix="ToggleInputMute",
            action_name=self.lm.get("actions.toggle-input-mute.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            },
        )
        self.add_action_holder(toggle_input_mute_action_holder)

        set_input_mute_action_holder = ActionHolder(
            plugin_base=self,
            action_base=SetInputMute,
            action_id_suffix="SetInputMute",
            action_name=self.lm.get("actions.set-input-mute.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            },
        )
        self.add_action_holder(set_input_mute_action_holder)

        input_dial_holder = ActionHolder(
            plugin_base=self,
            action_base=InputDial,
            action_id_suffix="InputDial",
            action_name=self.lm.get("actions.input-dial.name"),
            action_support={
                Input.Key: ActionInputSupport.UNTESTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNSUPPORTED,
            },
        )
        self.add_action_holder(input_dial_holder)

        # Scenes
        switch_scene_action_holder = ActionHolder(
            plugin_base=self,
            action_base=SwitchScene,
            action_id_suffix="SwitchScene",
            action_name=self.lm.get("actions.switch-scene.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.UNTESTED,
            },
        )
        self.add_action_holder(switch_scene_action_holder)

        # Scene Items
        toggle_scene_item_enabled_action_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleSceneItemEnabled,
            action_id_suffix="ToggleSceneItemEnabled",
            action_name=self.lm.get("actions.toggle-scene-item-enabled.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            },
        )
        self.add_action_holder(toggle_scene_item_enabled_action_holder)

        set_scene_item_enabled_action_holder = ActionHolder(
            plugin_base=self,
            action_base=SetSceneItemEnabled,
            action_id_suffix="SetSceneItemEnabled",
            action_name=self.lm.get("actions.set-scene-item-enabled.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            },
        )
        self.add_action_holder(set_scene_item_enabled_action_holder)

        # Scene Collections
        switch_scene_collection_action_holder = ActionHolder(
            plugin_base=self,
            action_base=SwitchSceneCollection,
            action_id_suffix="SwitchSceneCollection",
            action_name=self.lm.get("actions.switch-scene-collection.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            },
        )
        self.add_action_holder(switch_scene_collection_action_holder)

        toggle_filter_holder = ActionHolder(
            plugin_base=self,
            action_base=ToggleFilter,
            action_id_suffix="ToggleSceneFilter",
            action_name=self.lm.get("actions.toggle-filter.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            },
        )
        self.add_action_holder(toggle_filter_holder)

        set_filter_holder = ActionHolder(
            plugin_base=self,
            action_base=SetFilter,
            action_id_suffix="SetSceneFilter",
            action_name=self.lm.get("actions.set-filter.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            },
        )
        self.add_action_holder(set_filter_holder)

        # OBS Stats
        obs_stats_holder = ActionHolder(
            plugin_base=self,
            action_base=OBSStats,
            action_id_suffix="OBSStats",
            action_name=self.lm.get("actions.obs-stats.name"),
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.SUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            },
        )
        self.add_action_holder(obs_stats_holder)

        # Load custom css
        self.add_css_stylesheet(os.path.join(self.PATH, "style.css"))

    def get_connected(self, connection_id="default"):
        try:
            return self.backend.get_connected(connection_id)
        except Exception as e:
            log.error(e)
            return False

    def migrate_connection_settings(self):
        settings = self.get_settings()
        if "connections" not in settings:
            ip = settings.get("ip", "localhost")
            port = settings.get("port", 4455)
            password = settings.get("password") or ""
            settings["connections"] = [
                {
                    "id": "default",
                    "name": "Default",
                    "ip": ip,
                    "port": int(port) if isinstance(port, (int, float)) or (isinstance(port, str) and port.isdigit()) else 4455,
                    "password": password
                }
            ]
            settings["default_connection"] = "default"
            self.set_settings(settings)

    def get_settings_area(self) -> Adw.PreferencesGroup:
        pref_group = Adw.PreferencesGroup()
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        pref_group.add(main_box)
        
        # Left sidebar
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left_box.set_size_request(200, -1)
        
        self.profile_listbox = Gtk.ListBox()
        self.profile_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        
        scroll_profiles = Gtk.ScrolledWindow()
        scroll_profiles.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll_profiles.set_child(self.profile_listbox)
        scroll_profiles.set_size_request(-1, 200)
        left_box.append(scroll_profiles)
        
        add_btn = Gtk.Button(label="Add Profile")
        add_btn.connect("clicked", self.on_add_profile)
        left_box.append(add_btn)
        
        # Right editor
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right_box.set_hexpand(True)
        
        self.name_row = Adw.EntryRow(title="Profile Name")
        self.ip_row = Adw.EntryRow(title="IP Address")
        self.port_row = Adw.SpinRow.new_with_range(0, 65535, 1)
        self.port_row.set_title("Port")
        self.password_row = Adw.PasswordEntryRow(title="Password")
        
        right_box.append(self.name_row)
        right_box.append(self.ip_row)
        right_box.append(self.port_row)
        right_box.append(self.password_row)
        
        self.status_info_label = Gtk.Label(label="")
        self.status_info_label.set_halign(Gtk.Align.START)
        right_box.append(self.status_info_label)
        
        # Action Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        test_btn = Gtk.Button(label="Test Connection")
        test_btn.connect("clicked", self.on_test_connection)
        
        del_btn = Gtk.Button(label="Delete Profile")
        del_btn.connect("clicked", self.on_delete_profile)
        
        save_btn = Gtk.Button(label="Save Profile")
        save_btn.connect("clicked", self.on_save_profile)
        save_btn.add_css_class("suggested-action")
        
        btn_box.append(test_btn)
        btn_box.append(del_btn)
        btn_box.append(save_btn)
        right_box.append(btn_box)
        
        main_box.append(left_box)
        main_box.append(right_box)
        
        self.profile_listbox.connect("row-selected", self.on_profile_selected)
        self.load_profiles_into_listbox()
        
        return pref_group

    def update_editor_sensitivity(self, sensitive):
        self.name_row.set_sensitive(sensitive)
        self.ip_row.set_sensitive(sensitive)
        self.port_row.set_sensitive(sensitive)
        self.password_row.set_sensitive(sensitive)

    def load_profiles_into_listbox(self):
        while True:
            row = self.profile_listbox.get_row_at_index(0)
            if row is None:
                break
            self.profile_listbox.remove(row)
            
        settings = self.get_settings()
        connections = settings.get("connections", [])
        self.profiles_by_row = {}
        
        for conn in connections:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=conn.get("name", "Unnamed"))
            label.set_halign(Gtk.Align.START)
            label.set_margin_start(10)
            label.set_margin_end(10)
            label.set_margin_top(6)
            label.set_margin_bottom(6)
            row.set_child(label)
            self.profile_listbox.append(row)
            self.profiles_by_row[row] = conn
            
        first_row = self.profile_listbox.get_row_at_index(0)
        if first_row:
            self.profile_listbox.select_row(first_row)
        else:
            self.on_profile_selected(self.profile_listbox, None)

    def on_profile_selected(self, listbox, row):
        if row is None or row not in self.profiles_by_row:
            self.active_profile_id = None
            self.update_editor_sensitivity(False)
            self.name_row.set_text("")
            self.ip_row.set_text("")
            self.port_row.set_value(4455)
            self.password_row.set_text("")
            self.status_info_label.set_label("")
            return
            
        profile = self.profiles_by_row[row]
        self.active_profile_id = profile["id"]
        self.update_editor_sensitivity(True)
        
        self.name_row.set_text(profile.get("name", ""))
        self.ip_row.set_text(profile.get("ip", "localhost"))
        try:
            self.port_row.set_value(int(profile.get("port", 4455)))
        except ValueError:
            self.port_row.set_value(4455)
        self.password_row.set_text(profile.get("password", ""))
        self.status_info_label.set_label("")
        self.status_info_label.remove_css_class("green")
        self.status_info_label.remove_css_class("red")

    def on_add_profile(self, button):
        settings = self.get_settings()
        connections = settings.setdefault("connections", [])
        
        new_id = str(uuid.uuid4())
        new_profile = {
            "id": new_id,
            "name": f"OBS Profile {len(connections) + 1}",
            "ip": "localhost",
            "port": 4455,
            "password": ""
        }
        connections.append(new_profile)
        self.set_settings(settings)
        
        self.load_profiles_into_listbox()
        
        for row, conn in self.profiles_by_row.items():
            if conn["id"] == new_id:
                self.profile_listbox.select_row(row)
                break

    def on_delete_profile(self, button):
        if not hasattr(self, "active_profile_id") or not self.active_profile_id:
            return
            
        settings = self.get_settings()
        connections = settings.get("connections", [])
        connections = [c for c in connections if c["id"] != self.active_profile_id]
        settings["connections"] = connections
        
        if settings.get("default_connection") == self.active_profile_id:
            settings["default_connection"] = connections[0]["id"] if connections else ""
            
        self.set_settings(settings)
        self.active_profile_id = None
        self.load_profiles_into_listbox()
        self.backend.reload_connections()

    def on_save_profile(self, button):
        if not hasattr(self, "active_profile_id") or not self.active_profile_id:
            return
            
        settings = self.get_settings()
        connections = settings.get("connections", [])
        
        for conn in connections:
            if conn["id"] == self.active_profile_id:
                conn["name"] = self.name_row.get_text().strip() or "Unnamed Profile"
                conn["ip"] = self.ip_row.get_text().strip()
                try:
                    conn["port"] = int(self.port_row.get_value())
                except ValueError:
                    conn["port"] = 4455
                conn["password"] = self.password_row.get_text()
                break
                
        self.set_settings(settings)
        selected_id = self.active_profile_id
        self.load_profiles_into_listbox()
        
        for row, conn in self.profiles_by_row.items():
            if conn["id"] == selected_id:
                self.profile_listbox.select_row(row)
                break
                
        self.backend.reload_connections()

    def on_test_connection(self, button):
        if not hasattr(self, "active_profile_id") or not self.active_profile_id:
            return
            
        host = self.ip_row.get_text().strip()
        port = int(self.port_row.get_value())
        password = self.password_row.get_text()
        
        self.status_info_label.set_label("Testing connection...")
        self.status_info_label.remove_css_class("green")
        self.status_info_label.remove_css_class("red")
        
        def run_test():
            result = self.backend.test_connection(host, port, password)
            GLib.idle_add(self.show_test_result, result)
            
        threading.Thread(target=run_test, daemon=True, name="test_connection").start()

    def show_test_result(self, result):
        if result.get("success"):
            version_info = result.get("version", "Connected")
            self.status_info_label.set_label(f"Success! OBS Version: {version_info}")
            self.status_info_label.add_css_class("green")
            self.status_info_label.remove_css_class("red")
        else:
            err = result.get("error", "Unknown error")
            self.status_info_label.set_label(f"Failed: {err}")
            self.status_info_label.add_css_class("red")
            self.status_info_label.remove_css_class("green")
