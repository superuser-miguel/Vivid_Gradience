# desktop_group.py
#
# Change the look of Adwaita, with ease
# Copyright (C) 2026, Vivid Gradience contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from subprocess import SubprocessError

from gi.repository import GLib, Gtk, Adw

from gradience.backend.constants import rootdir
from gradience.backend.logger import Logger

from gradience.backend.theming.desktop import DesktopSettings, BUTTON_LAYOUTS

logging = Logger()


@Gtk.Template(resource_path=f"{rootdir}/ui/desktop_group.ui")
class GradienceDesktopGroup(Adw.PreferencesGroup):
    __gtype_name__ = "GradienceDesktopGroup"

    gtk3_theme_row = Gtk.Template.Child("gtk3-theme-row")
    cursor_theme_row = Gtk.Template.Child("cursor-theme-row")
    dark_style_row = Gtk.Template.Child("dark-style-row")
    button_layout_row = Gtk.Template.Child("button-layout-row")
    split_warning_button = Gtk.Template.Child("split-warning-button")
    split_warning_label = Gtk.Template.Child("split-warning-label")

    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        self.toast_overlay = parent.toast_overlay

        self._updating = True
        try:
            self.desktop = DesktopSettings()
        except Exception as e:
            logging.warning(f"Desktop settings unavailable: {e}")
            self.desktop = None
            self.set_sensitive(False)
            return

        self.setup_rows()
        self._updating = False

    def _fill_combo(self, row, names, current):
        store = Gtk.StringList()
        selected = 0
        for i, name in enumerate(names):
            store.append(name)
            if name == current:
                selected = i
        row.set_model(store)
        row.set_selected(selected)

    def setup_rows(self):
        self.gtk3_names = self.desktop.gtk3_themes()
        current_gtk3 = self.desktop.get_gtk_theme()
        if current_gtk3 and current_gtk3 not in self.gtk3_names:
            self.gtk3_names.insert(0, current_gtk3)
        self._fill_combo(self.gtk3_theme_row, self.gtk3_names, current_gtk3)
        self.gtk3_theme_row.connect("notify::selected", self.on_gtk3_theme_changed)
        self._update_split_warning(current_gtk3)

        self.cursor_names = self.desktop.cursor_themes()
        current_cursor = self.desktop.get_cursor_theme()
        if current_cursor and current_cursor not in self.cursor_names:
            self.cursor_names.insert(0, current_cursor)
        self._fill_combo(self.cursor_theme_row, self.cursor_names, current_cursor)
        self.cursor_theme_row.connect("notify::selected", self.on_cursor_theme_changed)

        self.dark_style_row.set_active(
            self.desktop.get_color_scheme() == "prefer-dark")
        self.dark_style_row.connect("notify::active", self.on_dark_style_toggled)

        layouts = [label for _value, label in BUTTON_LAYOUTS]
        values = [value for value, _label in BUTTON_LAYOUTS]
        current_layout = self.desktop.get_button_layout()
        if current_layout not in values:
            values.insert(0, current_layout)
            layouts.insert(0, _("Current: {0}").format(current_layout))
        self.layout_values = values
        self._fill_combo(self.button_layout_row, layouts,
                         layouts[values.index(current_layout)])
        self.button_layout_row.set_selected(values.index(current_layout))
        self.button_layout_row.connect("notify::selected", self.on_button_layout_changed)

    # -- handlers --------------------------------------------------------

    def _selected_string(self, row, names):
        pos = row.get_selected()
        if pos == Gtk.INVALID_LIST_POSITION or pos >= len(names):
            return None
        return names[pos]

    def on_gtk3_theme_changed(self, *_args):
        if self._updating:
            return
        name = self._selected_string(self.gtk3_theme_row, self.gtk3_names)
        if not name:
            return
        try:
            self.desktop.set_gtk_theme(name)
        except (GLib.GError, SubprocessError) as e:
            logging.error("Failed to set the GTK 3 theme.", exc=e)
            return
        self._update_split_warning(name)

    def _update_split_warning(self, name):
        try:
            missing = self.desktop.gtk3_extension_missing(name)
        except Exception:
            missing = False
        self.split_warning_button.set_visible(missing)
        if missing:
            self.split_warning_label.set_label(_(
                "Flatpak applications resolve GTK 3 themes from the "
                "org.gtk.Gtk3theme.{0} extension, which is not installed — "
                "they will silently fall back to Adwaita while host "
                "applications use {0}.\n\nInstall it with:\n"
                "flatpak install org.gtk.Gtk3theme.{0}").format(name))

    def on_cursor_theme_changed(self, *_args):
        if self._updating:
            return
        name = self._selected_string(self.cursor_theme_row, self.cursor_names)
        if not name:
            return
        try:
            self.desktop.set_cursor_theme(name)
        except (GLib.GError, SubprocessError) as e:
            logging.error("Failed to set the cursor theme.", exc=e)

    def on_dark_style_toggled(self, *_args):
        if self._updating:
            return
        scheme = "prefer-dark" if self.dark_style_row.get_active() else "default"
        try:
            self.desktop.set_color_scheme(scheme)
        except (GLib.GError, SubprocessError) as e:
            logging.error("Failed to set the color scheme.", exc=e)

    def on_button_layout_changed(self, *_args):
        if self._updating:
            return
        pos = self.button_layout_row.get_selected()
        if pos == Gtk.INVALID_LIST_POSITION or pos >= len(self.layout_values):
            return
        try:
            self.desktop.set_button_layout(self.layout_values[pos])
        except (GLib.GError, SubprocessError) as e:
            logging.error("Failed to set the button layout.", exc=e)
