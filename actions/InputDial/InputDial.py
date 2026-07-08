from OBSActionBase import OBSActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.DeckManagement.InputIdentifier import Input, InputEvent
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase
from GtkHelper.GtkHelper import ComboRow
from GtkHelper.ColorButtonRow import ColorButtonRow

import os
import threading
import math
import time
from PIL import Image, ImageDraw, ImageFont
from loguru import logger as log

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
        self._update_loop_running = False

    def on_ready(self):
        # Connect to obs if not connected
        if self.backend is not None:
            if not self.plugin_base.get_connected():
                self.reconnect_obs()
        
        self.muted = None
        self.volume = None
        self.start_update_loop()
    
    def start_update_loop(self):
        if self._update_loop_running:
            return
        self._update_loop_running = True
        threading.Thread(target=self.update_loop, daemon=True, name="input_dial_update_loop").start()

    def update_loop(self):
        last_info_time = 0.0
        while self.get_is_present():
            current_time = time.time()
            # Fetch mute/volume settings from OBS every 500ms
            if current_time - last_info_time >= 0.5:
                self.fetch_volume_info()
                last_info_time = current_time
            
            # Redraw UI (uses cached meter peak level)
            self.update_ui()
            
            if self.get_settings().get("live_meter", False):
                time.sleep(0.08)
            else:
                time.sleep(0.2)
        self._update_loop_running = False

    def fetch_volume_info(self):
        if self.backend is None or not self.backend.get_connected():
            self.muted = True
            self.volume = 0
            return
            
        input_name = self.get_settings().get("input")
        if not input_name:
            self.muted = True
            self.volume = 0
            return
            
        try:
            status = self.backend.get_input_muted(input_name)
            if status is not None:
                self.muted = status["muted"]
            else:
                self.muted = True
                
            status = self.backend.get_input_volume(input_name)
            if status is not None:
                self.volume = self.db_to_volume(status["volume"])
            else:
                self.volume = 0
        except Exception as e:
            log.error(f"Error fetching volume info: {e}")

    def update_ui(self):
        img = self.render_image()
        self.set_label("")
        self.set_media(image=img, size=1.0, valign=0.0, halign=0.0)

    def get_font(self, size):
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        except Exception:
            try:
                import subprocess
                result = subprocess.run(["fc-match", "-f", "%{file}\n", "DejaVu Sans:style=Bold"], capture_output=True, text=True)
                path = result.stdout.strip()
                if path and os.path.exists(path):
                    return ImageFont.truetype(path, size)
            except Exception:
                pass
            return ImageFont.load_default()

    def render_image(self) -> Image.Image:
        is_dial = isinstance(self.input_ident, Input.Dial)
        width = 200 if is_dial else 100
        height = 100
        
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        
        settings = self.get_settings()
        input_name = settings.get("input", "No Input")
        muted = True if self.muted is None else self.muted
        volume = 0 if self.volume is None else self.volume
        
        default_icon_name = "input_muted.png" if muted else "input_unmuted.png"
        icon_path = self.validated_custom_icons.get(default_icon_name)
        if not icon_path or not os.path.exists(icon_path):
            icon_path = os.path.join(self.plugin_base.PATH, "assets", default_icon_name)
            
        try:
            icon_img = Image.open(icon_path).convert("RGBA")
        except Exception:
            icon_img = None
            
        font_title = self.get_font(14)
        font_percentage = self.get_font(18)
        
        if is_dial:
            # Draw input name
            draw.text((100, 20), input_name, font=font_title, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255), anchor="mm")
            
            # Draw icon
            icon_size = 40
            if icon_img:
                icon_img = icon_img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                canvas.paste(icon_img, (15, 45), icon_img)
                
            # Draw bar
            x0, y0, x1, y1 = 65, 75, 185, 85
            w = x1 - x0
            green_end = x0 + int(w * 0.667)
            yellow_end = x0 + int(w * 0.85)
            
            is_live = settings.get("live_meter", False)
            if is_live:
                # 1. Draw structured background scale (dim green, dim yellow, dim red)
                bg_mask = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                draw_bg_mask = ImageDraw.Draw(bg_mask)
                draw_bg_mask.rounded_rectangle([x0, y0, x1, y1], radius=5, fill=(255, 255, 255, 255))
                
                bg_texture = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                draw_bg_tex = ImageDraw.Draw(bg_texture)
                draw_bg_tex.rectangle([x0, y0, green_end, y1], fill=(0, 80, 20, 255))
                draw_bg_tex.rectangle([green_end, y0, yellow_end, y1], fill=(80, 60, 0, 255))
                draw_bg_tex.rectangle([yellow_end, y0, x1, y1], fill=(80, 15, 15, 255))
                
                canvas = Image.composite(bg_texture, canvas, bg_mask.getchannel('A'))
                draw = ImageDraw.Draw(canvas)
                
                # 2. Draw active volume fill
                peak = 0.0
                if self.backend and self.backend.get_connected():
                    peak = self.backend.get_input_volume_meter(input_name)
                
                if peak <= 0.001:
                    db_level = -60.0
                else:
                    db_level = max(-60.0, 20.0 * math.log10(peak))
                
                fill_pct = (db_level - (-60.0)) / 60.0
                if fill_pct > 0:
                    x_fill = x0 + int((x1 - x0) * fill_pct)
                    x_fill = max(x0 + 10, x_fill)
                    
                    bar_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                    draw_bar = ImageDraw.Draw(bar_img)
                    draw_bar.rounded_rectangle([x0, y0, x_fill, y1], radius=5, fill=(255, 255, 255, 255))
                    
                    texture = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                    draw_tex = ImageDraw.Draw(texture)
                    draw_tex.rectangle([x0, y0, green_end, y1], fill=(0, 255, 70, 255))
                    draw_tex.rectangle([green_end, y0, yellow_end, y1], fill=(255, 190, 0, 255))
                    draw_tex.rectangle([yellow_end, y0, x1, y1], fill=(255, 40, 50, 255))
                    
                    canvas = Image.composite(texture, canvas, bar_img.getchannel('A'))
                    draw = ImageDraw.Draw(canvas)
                
                # 3. Draw black separator lines on top
                draw.line([(green_end, y0), (green_end, y1)], fill=(0, 0, 0, 255), width=1)
                draw.line([(yellow_end, y0), (yellow_end, y1)], fill=(0, 0, 0, 255), width=1)
                
                # 4. Draw outer border
                draw.rounded_rectangle([x0, y0, x1, y1], radius=5, fill=None, outline=(0, 0, 0, 255), width=1)
            else:
                # Static color bar background
                draw.rounded_rectangle([x0, y0, x1, y1], radius=5, fill=(40, 40, 40, 255), outline=(0, 0, 0, 255), width=1)
                
                bar_color = tuple(settings.get("bar_color", [66, 133, 244, 255]))
                fill_pct = volume / 100.0
                if fill_pct > 0:
                    x_fill = x0 + int((x1 - x0) * fill_pct)
                    x_fill = max(x0 + 10, x_fill)
                    draw.rounded_rectangle([x0, y0, x_fill, y1], radius=5, fill=bar_color, outline=(0, 0, 0, 255), width=1)
                    
            # Draw percentage
            label = f"{volume}%"
            draw.text((185, 68), label, font=font_percentage, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255), anchor="rd")
        else:
            # Button layout
            icon_size = 48
            if icon_img:
                icon_img = icon_img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                canvas.paste(icon_img, (26, 15), icon_img)
                
            label = f"{volume}%"
            draw.text((50, 80), label, font=font_percentage, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255), anchor="mm")
            
        return canvas

    def get_config_rows(self) -> list:
        super_rows = super().get_config_rows()

        self.input_model = Gtk.StringList()
        self.input_row = Adw.ComboRow(model=self.input_model, title=self.plugin_base.lm.get("actions.input-dial-row.label"))

        self.color_row = ColorButtonRow(
            title="Volume Bar Color",
            default_color=(66, 133, 244, 255)
        )

        self.live_meter_row = Adw.ActionRow(title="Enable Live Meter")
        self.live_meter_switch = Gtk.Switch()
        self.live_meter_switch.set_valign(Gtk.Align.CENTER)
        self.live_meter_row.add_suffix(self.live_meter_switch)

        self.connect_signals()

        self.load_input_model()
        self.load_configs()

        super_rows.append(self.input_row)
        super_rows.append(self.color_row)
        super_rows.append(self.live_meter_row)
        return super_rows

    def connect_signals(self):
        self.input_row.connect("notify::selected", self.on_input_change)
        self.color_row.color_button.connect("color-set", self.on_color_changed)
        self.live_meter_switch.connect("notify::active", self.on_live_meter_changed)

    def disconnect_signals(self):
        try:
            self.input_row.disconnect_by_func(self.on_input_change)
        except TypeError:
            pass
        try:
            self.color_row.color_button.disconnect_by_func(self.on_color_changed)
        except TypeError:
            pass
        try:
            self.live_meter_switch.disconnect_by_func(self.on_live_meter_changed)
        except TypeError:
            pass
    
    def load_input_model(self):
        self.disconnect_signals()
        while self.input_model.get_n_items() > 0:
            self.input_model.remove(0)

        self.input_model.append("")

        if self.backend.get_connected():
            inputs = self.backend.get_inputs()
            if inputs is not None:
                for input in inputs:
                    self.input_model.append(input)

        self.connect_signals()

    def load_configs(self):
        self.load_selected_device()
        self.load_color_and_switch_defaults()

    def load_selected_device(self):
        self.disconnect_signals()
        settings = self.get_settings()
        configured_input = settings.get("input")

        if not configured_input:
            self.input_row.set_selected(0)
            self.connect_signals()
            return

        for i, input_name in enumerate(self.input_model):
            if input_name.get_string() == configured_input:
                self.input_row.set_selected(i)
                self.connect_signals()
                return
            
        self.input_row.set_selected(0)
        self.connect_signals()

    def load_color_and_switch_defaults(self):
        self.disconnect_signals()
        settings = self.get_settings()
        
        color = settings.get("bar_color", [66, 133, 244, 255])
        self.color_row.color = tuple(color)
        
        self.live_meter_switch.set_active(settings.get("live_meter", False))
        
        self.connect_signals()
    
    def on_input_change(self, *args):
        settings = self.get_settings()
        selected_index = self.input_row.get_selected()
        if selected_index == Gtk.INVALID_LIST_POSITION or selected_index < 0 or selected_index >= self.input_model.get_n_items():
            settings["input"] = ""
        else:
            settings["input"] = self.input_model[selected_index].get_string()
        self.set_settings(settings)
        self.fetch_volume_info()
        self.update_ui()

    def on_color_changed(self, *args):
        settings = self.get_settings()
        settings["bar_color"] = list(self.color_row.color)
        self.set_settings(settings)
        self.update_ui()

    def on_live_meter_changed(self, switch, *args):
        settings = self.get_settings()
        settings["live_meter"] = switch.get_active()
        self.set_settings(settings)
        self.update_ui()

    def event_callback(self, event: InputEvent, data: dict = None):
        if event == Input.Key.Events.DOWN or event == Input.Dial.Events.DOWN:
            self.mute_toggle()
        if str(event) == str(Input.Dial.Events.TURN_CW):
            self.volume_change(+5)
        if str(event) == str(Input.Dial.Events.TURN_CCW):
            self.volume_change(-5)

    def mute_toggle(self):
        if self.backend is None or not self.backend.get_connected():
            self.show_error()
            return

        input_name = self.get_settings().get("input")
        if input_name in [None, ""]:
            self.show_error()
            return

        self.muted = not self.muted
        threading.Thread(target=self._set_mute_backend, args=(input_name, self.muted), daemon=True).start()
        self.update_ui()

    def _set_mute_backend(self, input_name, muted):
        try:
            self.backend.set_input_muted(input_name, muted)
        except Exception as e:
            log.error(f"Error setting mute: {e}")
    
    def volume_change(self, diff):
        if self.backend is None or not self.backend.get_connected():
            self.show_error()
            return

        input_name = self.get_settings().get("input")
        if input_name in [None, ""]:
            self.show_error()
            return
        
        self.volume += diff
        if self.volume < 0:
            self.volume = 0
        if self.volume > 100:
            self.volume = 100
        
        threading.Thread(target=self._set_volume_backend, args=(input_name, self.volume), daemon=True).start()
        self.update_ui()

    def _set_volume_backend(self, input_name, volume):
        try:
            self.backend.set_input_volume(input_name, self.volume_to_db(volume))
        except Exception as e:
            log.error(f"Error setting volume: {e}")

    def on_tick(self):
        self.start_update_loop()

    def on_connection_established(self):
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