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
        self.stat_1_model = None
        self.stat_1_row = None
        self.stat_2_model = None
        self.stat_2_row = None
        self.stat_3_model = None
        self.stat_3_row = None

    def on_ready(self):
        # Connect to obs if not connected
        if self.plugin_base.backend is not None:
            if not self.plugin_base.get_connected():
                self.reconnect_obs()

        self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "stats.png"), size=0.85)
        self.on_tick()

    def get_config_rows(self) -> list:
        super_rows = super().get_config_rows()

        # Stats count selection row
        self.stats_count_model = Gtk.StringList()
        self.stats_count_model.append("1")
        self.stats_count_model.append("2")
        self.stats_count_model.append("3")

        self.stats_count_row = Adw.ComboRow(
            model=self.stats_count_model, 
            title=self.plugin_base.lm.get("actions.obs-stats.stats-count-row.label")
        )

        # Stat 1 dropdown row
        self.stat_1_model = Gtk.StringList()
        self.stat_1_model.append(self.plugin_base.lm.get("actions.obs-stats.cpu"))
        self.stat_1_model.append(self.plugin_base.lm.get("actions.obs-stats.fps"))
        self.stat_1_model.append(self.plugin_base.lm.get("actions.obs-stats.stream"))

        self.stat_1_row = Adw.ComboRow(
            model=self.stat_1_model,
            title=self.plugin_base.lm.get("actions.obs-stats.stat1.label")
        )

        # Stat 2 dropdown row
        self.stat_2_model = Gtk.StringList()
        self.stat_2_model.append(self.plugin_base.lm.get("actions.obs-stats.cpu"))
        self.stat_2_model.append(self.plugin_base.lm.get("actions.obs-stats.fps"))
        self.stat_2_model.append(self.plugin_base.lm.get("actions.obs-stats.stream"))

        self.stat_2_row = Adw.ComboRow(
            model=self.stat_2_model,
            title=self.plugin_base.lm.get("actions.obs-stats.stat2.label")
        )

        # Stat 3 dropdown row
        self.stat_3_model = Gtk.StringList()
        self.stat_3_model.append(self.plugin_base.lm.get("actions.obs-stats.cpu"))
        self.stat_3_model.append(self.plugin_base.lm.get("actions.obs-stats.fps"))
        self.stat_3_model.append(self.plugin_base.lm.get("actions.obs-stats.stream"))

        self.stat_3_row = Adw.ComboRow(
            model=self.stat_3_model,
            title=self.plugin_base.lm.get("actions.obs-stats.stat3.label")
        )

        self.connect_signals()
        self.load_configs()

        super_rows.append(self.stats_count_row)
        super_rows.append(self.stat_1_row)
        super_rows.append(self.stat_2_row)
        super_rows.append(self.stat_3_row)
        return super_rows

    def connect_signals(self):
        self.stats_count_row.connect("notify::selected", self.on_change_stats_count)
        self.stat_1_row.connect("notify::selected", self.on_change_stat_1)
        self.stat_2_row.connect("notify::selected", self.on_change_stat_2)
        self.stat_3_row.connect("notify::selected", self.on_change_stat_3)

    def disconnect_signals(self):
        try:
            self.stats_count_row.disconnect_by_func(self.on_change_stats_count)
        except TypeError: pass
        try:
            self.stat_1_row.disconnect_by_func(self.on_change_stat_1)
        except TypeError: pass
        try:
            self.stat_2_row.disconnect_by_func(self.on_change_stat_2)
        except TypeError: pass
        try:
            self.stat_3_row.disconnect_by_func(self.on_change_stat_3)
        except TypeError: pass

    def get_option_by_index(self, index: int) -> str:
        options = ["CPU", "FPS", "Stream"]
        if 0 <= index < len(options):
            return options[index]
        return "CPU"

    def get_index_by_option(self, option: str) -> int:
        options = ["CPU", "FPS", "Stream"]
        if option in options:
            return options.index(option)
        return 0

    def load_configs(self):
        self.disconnect_signals()
        settings = self.get_settings()
        
        count = settings.setdefault("stats_count", "3")
        stat_1 = settings.setdefault("stat_1", "CPU")
        stat_2 = settings.setdefault("stat_2", "FPS")
        stat_3 = settings.setdefault("stat_3", "Stream")

        # Load stats_count selection
        count_idx = 2
        for i, val in enumerate(self.stats_count_model):
            if val.get_string() == count:
                count_idx = i
                break
        self.stats_count_row.set_selected(count_idx)

        self.stat_1_row.set_selected(self.get_index_by_option(stat_1))
        self.stat_2_row.set_selected(self.get_index_by_option(stat_2))
        self.stat_3_row.set_selected(self.get_index_by_option(stat_3))

        self.update_row_visibilities()
        self.connect_signals()

    def update_row_visibilities(self):
        selected_index = self.stats_count_row.get_selected()
        if selected_index == Gtk.INVALID_LIST_POSITION:
            return
        count = self.stats_count_model[selected_index].get_string()
        if count == "1":
            self.stat_1_row.set_visible(True)
            self.stat_2_row.set_visible(False)
            self.stat_3_row.set_visible(False)
        elif count == "2":
            self.stat_1_row.set_visible(True)
            self.stat_2_row.set_visible(True)
            self.stat_3_row.set_visible(False)
        else: # "3"
            self.stat_1_row.set_visible(True)
            self.stat_2_row.set_visible(True)
            self.stat_3_row.set_visible(True)

    def on_change_stats_count(self, *args):
        settings = self.get_settings()
        selected_index = self.stats_count_row.get_selected()
        if selected_index != Gtk.INVALID_LIST_POSITION:
            settings["stats_count"] = self.stats_count_model[selected_index].get_string()
            self.set_settings(settings)
            self.update_row_visibilities()
            self.on_tick()

    def on_change_stat_1(self, *args):
        settings = self.get_settings()
        idx = self.stat_1_row.get_selected()
        if idx != Gtk.INVALID_LIST_POSITION:
            settings["stat_1"] = self.get_option_by_index(idx)
            self.set_settings(settings)
            self.on_tick()

    def on_change_stat_2(self, *args):
        settings = self.get_settings()
        idx = self.stat_2_row.get_selected()
        if idx != Gtk.INVALID_LIST_POSITION:
            settings["stat_2"] = self.get_option_by_index(idx)
            self.set_settings(settings)
            self.on_tick()

    def on_change_stat_3(self, *args):
        settings = self.get_settings()
        idx = self.stat_3_row.get_selected()
        if idx != Gtk.INVALID_LIST_POSITION:
            settings["stat_3"] = self.get_option_by_index(idx)
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

        # Prepare strings
        stat_strings = {}
        
        cpu_val = stats.get('cpu_usage', 0.0)
        stat_strings["CPU"] = f"CPU: {cpu_val:.1f}%"
        
        fps_val = stats.get('fps', 0.0)
        target_fps = stats.get('target_fps', 60)
        stat_strings["FPS"] = f"FPS: {int(round(fps_val))}/{target_fps}"

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
        stat_strings["Stream"] = bw_str

        # Get settings
        settings = self.get_settings()
        count = settings.get("stats_count", "3")
        
        # Load selections for each slot
        stat_1_sel = settings.get("stat_1", "CPU")
        stat_2_sel = settings.get("stat_2", "FPS")
        stat_3_sel = settings.get("stat_3", "Stream")

        if count == "1":
            self.set_top_label(None)
            self.set_center_label(stat_strings.get(stat_1_sel, ""))
            self.set_bottom_label(None)
        elif count == "2":
            self.set_top_label(stat_strings.get(stat_1_sel, ""))
            self.set_center_label(None)
            self.set_bottom_label(stat_strings.get(stat_2_sel, ""))
        else: # "3"
            self.set_top_label(stat_strings.get(stat_1_sel, ""))
            self.set_center_label(stat_strings.get(stat_2_sel, ""))
            self.set_bottom_label(stat_strings.get(stat_3_sel, ""))
