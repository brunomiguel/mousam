import gi
from gi.repository import Gtk, Adw, GLib
from .config import settings
from .constants import icons, condition
from gettext import gettext as _

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

class CompactWeather(Gtk.Overlay):
    """
    A premium minimalist compact view of the current weather.
    """
    def __init__(self, on_back_clicked, **kwargs):
        super().__init__(**kwargs)
        self.on_back_clicked = on_back_clicked
        self._build_ui()

    def _build_ui(self):
        from .CORE_weatherData import current_weather_data as data, air_apllution_data as aq_data
        from .constants import icons, condition
        from .utils import JsonProcessor, get_timezone_from_selected_city
        import datetime
        from zoneinfo import ZoneInfo

        self.add_css_class("compact-container")
        self.set_valign(Gtk.Align.FILL)
        self.set_halign(Gtk.Align.FILL)
        self.set_size_request(280, 220)

        # Apply dynamic weather background
        if settings.is_using_dynamic_bg:
            from .constants import bg_css
            weather_code = data.weathercode.get("data")
            is_day = data.is_day.get("data")
            code_key = str(weather_code) + ("n" if is_day == 0 else "")
            css_class = bg_css.get(code_key, "")
            if css_class:
                self.add_css_class(css_class)

        # 3. Content Layer (Using a single Grid for positioning)
        grid = Gtk.Grid()
        grid.set_column_spacing(5)
        grid.set_row_spacing(0)
        grid.set_margin_start(25)
        grid.set_margin_end(25)
        grid.set_margin_top(25)
        grid.set_margin_bottom(25)
        self.add_overlay(grid)

        # City
        city_list = JsonProcessor.str_list_to_json(settings.added_cities)
        selected_city_str = settings.selected_city
        city_name = "Unknown"
        for city in city_list:
            if f"{city.get('latitude')},{city.get('longitude')}" == selected_city_str:
                city_name = city.get("name")
                break
        
        lbl_city = Gtk.Label(label=city_name)
        lbl_city.set_halign(Gtk.Align.START)
        lbl_city.add_css_class("text-2a")
        lbl_city.add_css_class("bold-1")
        lbl_city.add_css_class("light-2")
        grid.attach(lbl_city, 0, 0, 1, 1)

        # Condition
        weather_code = data.weathercode.get("data")
        lbl_cond = Gtk.Label(label=condition.get(str(weather_code), "Unknown"))
        lbl_cond.set_halign(Gtk.Align.START)
        lbl_cond.add_css_class("text-3")
        grid.attach(lbl_cond, 0, 1, 1, 1)

        # --- Top-Right: Icon ---
        icon_path = icons.get(str(weather_code), icons.get("unknown"))
        if data.is_day.get("data") == 0:
            icon_path = icons.get(str(weather_code) + "n", icon_path)

        img_cond = Gtk.Image.new_from_file(icon_path)
        img_cond.set_pixel_size(70)
        img_cond.set_halign(Gtk.Align.END)
        img_cond.set_valign(Gtk.Align.CENTER)
        grid.attach(img_cond, 2, 0, 1, 2) # Icon in top-right, spanning row 0 and 1

        # --- Spacer ---
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        grid.attach(spacer, 0, 2, 1, 1)

        # --- Bottom-Left Corner: Temp ---
        lbl_temp = Gtk.Label(label=f"{data.temperature_2m.get('data'):.0f}°")
        lbl_temp.set_halign(Gtk.Align.START)
        lbl_temp.set_valign(Gtk.Align.START)
        lbl_temp.set_margin_top(25)
        lbl_temp.add_css_class("compact-temp")
        grid.attach(lbl_temp, 0, 3, 1, 1) # Span 2 columns to stay in the corner

        # --- Bottom-Right: Extra Details ---
        details_grid = Gtk.Grid()
        details_grid.set_column_spacing(8)
        details_grid.set_row_spacing(0)
        details_grid.set_valign(Gtk.Align.START)
        details_grid.set_halign(Gtk.Align.END)
        details_grid.set_margin_top(15)
        details_grid.set_hexpand(True)
        grid.attach(details_grid, 2, 3, 1, 1)

        def add_detail_row(label_text, value_text, row):
            lbl_label = Gtk.Label(label=label_text)
            lbl_label.set_halign(Gtk.Align.START)
            lbl_label.add_css_class("compact-detail-label")
            
            lbl_value = Gtk.Label(label=value_text)
            lbl_value.set_halign(Gtk.Align.END)
            lbl_value.add_css_class("compact-detail-value")
            
            details_grid.attach(lbl_label, 0, row, 1, 1)
            details_grid.attach(lbl_value, 1, row, 1, 1)
            return lbl_value

        # Time/Date Row (Spanning both columns)
        self.lbl_time_val = Gtk.Label()
        self.lbl_time_val.set_halign(Gtk.Align.END)
        self.lbl_time_val.add_css_class("compact-detail-value")
        self.lbl_time_val.add_css_class("compact-time-value")
        self.lbl_time_val.set_use_markup(True)
        self.lbl_time_val.set_margin_bottom(5)
        
        self.target_tz = ZoneInfo(get_timezone_from_selected_city())
        now = datetime.datetime.now(self.target_tz)
        date_str = now.strftime("%d %B")
        time_str = now.strftime("%H:%M" if settings.is_using_24h_clock else "%I:%M %p")
        self.lbl_time_val.set_markup(f"{date_str} • {time_str}")
        
        details_grid.attach(self.lbl_time_val, 0, 0, 2, 1)

        def update_clock():
            fmt = "%H:%M" if settings.is_using_24h_clock else "%I:%M %p"
            now = datetime.datetime.now(self.target_tz)
            d_str = now.strftime("%d %B")
            t_str = now.strftime(fmt)
            self.lbl_time_val.set_markup(f"{d_str} • {t_str}")
            return True
        
        GLib.timeout_add_seconds(1, update_clock)

        def get_wind_dir(deg):
            dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            idx = int((deg + 11.25) / 22.5) % 16
            return dirs[idx]

        wind_deg = data.winddirection_10m.get('data')
        wind_dir = get_wind_dir(wind_deg)
        
        aqi = aq_data.get("current_us_aqi", "--")
        add_detail_row(_("AQI"), str(aqi), 4)
        add_detail_row(_("Wind"), f"{data.windspeed_10m.get('data')} {data.windspeed_10m.get('unit')} • {wind_dir}", 1)
        add_detail_row(_("Hum."), f"{data.relativehumidity_2m.get('data')} %", 2)
        add_detail_row(_("Pres."), f"{data.surface_pressure.get('data')} {data.surface_pressure.get('unit')}", 3)
        

        # Back Button (Top Right corner) - Hidden by default, shown on hover
        self.btn_back = Gtk.Button()
        self.btn_back.set_icon_name("go-previous-symbolic")
        self.btn_back.add_css_class("flat")
        self.btn_back.add_css_class("circular")
        self.btn_back.set_halign(Gtk.Align.END)
        self.btn_back.set_valign(Gtk.Align.START)
        self.btn_back.set_margin_top(5)
        self.btn_back.set_margin_end(5)
        self.btn_back.connect("clicked", lambda _: self.on_back_clicked())
        self.btn_back.set_visible(False)
        self.add_overlay(self.btn_back)

        # Hover effect to show/hide back button
        motion_ctrl = Gtk.EventControllerMotion()
        motion_ctrl.connect("enter", self._on_hover_enter)
        motion_ctrl.connect("leave", self._on_hover_leave)
        self.add_controller(motion_ctrl)

    def _on_hover_enter(self, controller, x, y):
        self.btn_back.set_visible(True)

    def _on_hover_leave(self, controller):
        self.btn_back.set_visible(False)

class CompactWeatherWindow(Adw.ApplicationWindow):
    def __init__(self, app, on_back_to_normal, **kwargs):
        super().__init__(application=app, **kwargs)
        self.on_back_to_normal = on_back_to_normal
        self.set_title(_("Mousam Compact"))
        self.add_css_class("compact-window")
        self.set_default_size(280, 220)
        self.set_resizable(False)
        self.set_decorated(False)
        
        # 1. Create a WindowHandle to make the whole window draggable
        handle = Gtk.WindowHandle()
        self.set_content(handle)

        # 2. Put the compact weather view inside the handle
        self.compact_view = CompactWeather(on_back_clicked=self.on_back_to_normal)
        handle.set_child(self.compact_view)
