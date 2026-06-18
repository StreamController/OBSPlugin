from plugins.com_oparada1988_OBS_Plus.OBSActionBase import OBSActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

import os
import threading

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

class OBSStats(OBSActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats_count_model = None
        self.stats_count_row = None

    def on_ready(self):
        # Connect to obs if not connected
        if self.plugin_base.backend is not None:
            if not self.plugin_base.get_connected():
                self.reconnect_obs()

        self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "stats.png"), size=0.85)
        self.on_tick()

    def get_config_rows(self) -> list:
        super_rows = super().get_config_rows()

        self.stats_count_model = Gtk.StringList()
        self.stats_count_model.append("1")
        self.stats_count_model.append("2")
        self.stats_count_model.append("3")

        self.stats_count_row = Adw.ComboRow(
            model=self.stats_count_model, 
            title=self.plugin_base.lm.get("actions.obs-stats.stats-count-row.label")
        )

        self.connect_signals()
        self.load_configs()

        super_rows.append(self.stats_count_row)
        return super_rows

    def connect_signals(self):
        self.stats_count_row.connect("notify::selected", self.on_change_stats_count)

    def disconnect_signals(self):
        try:
            self.stats_count_row.disconnect_by_func(self.on_change_stats_count)
        except TypeError:
            pass

    def load_configs(self):
        self.disconnect_signals()
        settings = self.get_settings()
        count = settings.setdefault("stats_count", "3")

        for i, val in enumerate(self.stats_count_model):
            if val.get_string() == count:
                self.stats_count_row.set_selected(i)
                self.connect_signals()
                return

        # default to 3 stats if invalid
        self.stats_count_row.set_selected(2)
        self.connect_signals()

    def on_change_stats_count(self, *args):
        settings = self.get_settings()
        selected_index = self.stats_count_row.get_selected()
        if selected_index != Gtk.INVALID_LIST_POSITION:
            settings["stats_count"] = self.stats_count_model[selected_index].get_string()
            self.set_settings(settings)
            self.on_tick()

    def on_tick(self):
        threading.Thread(target=self.update_stats, daemon=True, name="update_stats").start()

    def update_stats(self):
        if self.plugin_base.backend is None or not self.plugin_base.backend.get_connected():
            self.set_top_label(None)
            self.set_center_label("Offline")
            self.set_bottom_label(None)
            return

        stats = self.plugin_base.backend.get_obs_stats()
        if stats is None:
            self.set_top_label(None)
            self.set_center_label("Offline")
            self.set_bottom_label(None)
            return

        cpu_str = f"CPU: {stats.get('cpu_usage', 0.0):.1f}%"
        fps_str = f"FPS: {int(stats.get('fps', 0.0))}"

        if stats.get("streaming"):
            bw = stats.get("bandwidth", 0.0)
            if bw > 1000.0:
                bw_str = f"Live: {bw/1000.0:.1f}M"
            else:
                bw_str = f"Live: {int(bw)}k"
        elif stats.get("reconnecting"):
            bw_str = "Reconn..."
        else:
            bw_str = "Stream Off"

        settings = self.get_settings()
        count = settings.get("stats_count", "3")

        if count == "1":
            self.set_top_label(None)
            self.set_center_label(bw_str)
            self.set_bottom_label(None)
        elif count == "2":
            self.set_top_label(cpu_str)
            self.set_center_label(None)
            self.set_bottom_label(fps_str)
        else: # "3"
            self.set_top_label(cpu_str)
            self.set_center_label(fps_str)
            self.set_bottom_label(bw_str)
