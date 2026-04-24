import gi
from gi.repository import Gtk, Adw, GLib
from .config import settings
from .constants import icons, condition, bg_css
from gettext import gettext as _

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

class CompactWeather(Gtk.Overlay):
    """
    A premium minimalist compact view of the current weather.
    Shows loader until weather & air quality data are both available.
    """
    def __init__(self, on_back_clicked, **kwargs):
        super().__init__(**kwargs)
        self.on_back_clicked = on_back_clicked
        
        self.add_css_class("compact-container")
        self.set_valign(Gtk.Align.FILL)
        self.set_halign(Gtk.Align.FILL)
        self.set_size_request(280, 220)

        # Main stack to switch between loader and content
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.set_child(self.stack)

        # Back Button (Always available as overlay)
        self._setup_back_button()

        # Start checking for data (both weather and air pollution)
        self._check_all_data_ready()

    def _is_data_ready(self):
        """Return True only when both weather and air pollution data exist."""
        from .CORE_weatherData import current_weather_data, air_apllution_data
        return current_weather_data is not None and air_apllution_data is not None

    def _check_all_data_ready(self):
        """Poll every 500ms until all data is loaded, then build UI."""
        if not self._is_data_ready():
            # Show loader if not already showing
            if not self.stack.get_child_by_name("loader"):
                spinner = Adw.Spinner()
                spinner.set_size_request(32, 32)
                spinner.set_halign(Gtk.Align.CENTER)
                spinner.set_valign(Gtk.Align.CENTER)
                self.stack.add_named(spinner, "loader")
            self.stack.set_visible_child_name("loader")
            GLib.timeout_add(500, self._check_all_data_ready)
            return False
        
        # All data is ready → build the UI (and background)
        self._build_ui()
        return False

    def _build_ui(self):
        from .CORE_weatherData import current_weather_data as data, air_apllution_data as aq_data
        from .utils import JsonProcessor, get_timezone_from_selected_city
        import datetime
        from zoneinfo import ZoneInfo

        # Remove loader from stack (no longer needed)
        loader = self.stack.get_child_by_name("loader")
        if loader:
            self.stack.remove(loader)

        # 1. Apply dynamic background to the root window (async for safety)
        if settings.is_using_dynamic_bg:
            weather_code = data.weathercode.get("data", 0)
            is_day = data.is_day.get("data", 1)
            code_key = f"{weather_code}{'n' if is_day == 0 else ''}"
            css_class = bg_css.get(code_key, "")
            
            def update_root_bg():
                root = self.get_root()
                if root and css_class:
                    valid_bgs = set(bg_css.values())
                    for cls in root.get_css_classes():
                        if cls in valid_bgs:
                            root.remove_css_class(cls)
                    root.add_css_class(css_class)
                return False  # run only once
            
            GLib.idle_add(update_root_bg)

        # 2. Content Layer (Grid layout)
        grid = Gtk.Grid()
        grid.set_column_spacing(5)
        grid.set_row_spacing(0)
        grid.set_margin_start(25)
        grid.set_margin_end(25)
        grid.set_margin_top(25)
        grid.set_margin_bottom(25)
        self.add_overlay(grid)

        # ---- City ----
        city_list = JsonProcessor.str_list_to_json(settings.added_cities)
        selected_city_str = settings.selected_city
        city_name = "Unknown"
        for city in city_list:
            if f"{city.get('latitude')},{city.get('longitude')}" == selected_city_str:
                city_name = city.get("name")
                break
        if len(city_name) > 11:
            city_name = city_name[:8] + "..."

        lbl_city = Gtk.Label(label=city_name)
        lbl_city.set_halign(Gtk.Align.START)
        lbl_city.add_css_class("text-2a")
        lbl_city.add_css_class("bold-1")
        lbl_city.add_css_class("light-2")
        grid.attach(lbl_city, 0, 0, 1, 1)

        # ---- Condition ----
        weather_code = data.weathercode.get("data", 0)
        lbl_cond = Gtk.Label(label=condition.get(str(weather_code), condition.get("0", "Unknown")))
        lbl_cond.set_halign(Gtk.Align.START)
        lbl_cond.add_css_class("text-3")
        grid.attach(lbl_cond, 0, 1, 1, 1)

        # ---- Weather Icon ----
        icon_path = icons.get(str(weather_code), icons.get("unknown"))
        is_day_val = data.is_day.get("data", 1)
        if is_day_val == 0:
            icon_path = icons.get(str(weather_code) + "n", icon_path)

        img_cond = Gtk.Image.new_from_file(icon_path)
        img_cond.set_pixel_size(70)
        img_cond.set_halign(Gtk.Align.END)
        img_cond.set_valign(Gtk.Align.CENTER)
        grid.attach(img_cond, 2, 0, 1, 2)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        grid.attach(spacer, 0, 2, 1, 1)

        # ---- Temperature ----
        temp_val = data.temperature_2m.get('data')
        temp_str = f"{temp_val:.0f}°" if temp_val is not None else "--°"
        lbl_temp = Gtk.Label(label=temp_str)
        lbl_temp.set_halign(Gtk.Align.START)
        lbl_temp.set_valign(Gtk.Align.START)
        lbl_temp.set_margin_top(25)
        lbl_temp.add_css_class("compact-temp")
        grid.attach(lbl_temp, 0, 3, 1, 1)

        # ---- Extra Details Grid ----
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

        # Time / Date (live updating)
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

        # Wind direction helper
        def get_wind_dir(deg):
            if deg is None:
                return "--"
            dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            idx = int((deg + 11.25) / 22.5) % 16
            return dirs[idx]

        wind_deg = data.winddirection_10m.get('data')
        wind_dir = get_wind_dir(wind_deg)
        wind_speed = data.windspeed_10m.get('data')
        wind_speed_str = f"{wind_speed} {data.windspeed_10m.get('unit')}" if wind_speed is not None else "--"
        add_detail_row(_("Wind"), f"{wind_speed_str} • {wind_dir}", 1)

        hum = data.relativehumidity_2m.get('data')
        hum_str = f"{hum} %" if hum is not None else "-- %"
        add_detail_row(_("Hum."), hum_str, 2)

        pres = data.surface_pressure.get('data')
        pres_str = f"{pres} {data.surface_pressure.get('unit')}" if pres is not None else "--"
        add_detail_row(_("Pres."), pres_str, 3)

        # ---- AQI (now always present because data is ready) ----
        lbl_aqi_label = Gtk.Label(label=_("AQI"))
        lbl_aqi_label.set_halign(Gtk.Align.START)
        lbl_aqi_label.add_css_class("compact-detail-label")
        details_grid.attach(lbl_aqi_label, 0, 4, 1, 1)

        lbl_aqi_val = Gtk.Label()
        lbl_aqi_val.add_css_class("compact-detail-value")
        lbl_aqi_val.set_halign(Gtk.Align.END)
        aqi_value = aq_data.get("current_us_aqi", "--") if aq_data else "--"
        lbl_aqi_val.set_label(str(aqi_value))
        details_grid.attach(lbl_aqi_val, 1, 4, 1, 1)

        # Finally, hide the loader stack and show the content
        self.stack.set_visible_child(grid)

    def _setup_back_button(self):
        self.btn_back = Gtk.Button()
        self.btn_back.set_icon_name("view-fullscreen-symbolic")
        self.btn_back.add_css_class("flat")
        self.btn_back.add_css_class("circular")
        self.btn_back.set_halign(Gtk.Align.END)
        self.btn_back.set_valign(Gtk.Align.START)
        self.btn_back.set_margin_top(5)
        self.btn_back.set_margin_end(5)
        self.btn_back.connect("clicked", lambda _: self.on_back_clicked())
        self.btn_back.set_visible(False)
        self.add_overlay(self.btn_back)

        motion_ctrl = Gtk.EventControllerMotion()
        motion_ctrl.connect("enter", self._on_hover_enter)
        motion_ctrl.connect("leave", self._on_hover_leave)
        self.add_controller(motion_ctrl)

    def _on_hover_enter(self, controller, x, y):
        self.btn_back.set_visible(True)

    def _on_hover_leave(self, controller):
        self.btn_back.set_visible(False)


class CompactWeatherWindow(Adw.ApplicationWindow):
    def __init__(self, app, bg_classes=None, on_back_to_normal=None, **kwargs):
        super().__init__(application=app, **kwargs)
        self.on_back_to_normal = on_back_to_normal
        self.set_title(_("Mousam Compact"))
        self.set_default_size(280, 220)
        self.set_resizable(False)
        self.set_decorated(False)
        self.add_css_class("compact-window")
        if settings.is_using_dynamic_bg and bg_classes:
            from .constants import bg_css
            valid_bgs = set(bg_css.values())
            for cls in bg_classes:
                if cls in valid_bgs:
                    self.add_css_class(cls)

        # WindowHandle to make the whole window draggable
        handle = Gtk.WindowHandle()
        self.set_content(handle)

        self.compact_view = CompactWeather(on_back_clicked=self.on_back_to_normal)
        handle.set_child(self.compact_view)