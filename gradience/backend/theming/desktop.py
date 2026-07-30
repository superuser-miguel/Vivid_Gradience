# desktop.py
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

"""The desktop-wide appearance settings inherited from GNOME Tweaks.

Every operation here is a gsettings key — set it wrong and you set it back.
The one piece of real knowledge is the Flatpak base-theme split: sandboxed
applications resolve `interface.gtk-theme` from `org.gtk.Gtk3theme.<name>`
runtime extensions, not from the host's theme directories, so a host-only
theme silently leaves every Flatpak on stock Adwaita. The picker's job is
to say so at the moment the choice is made.
"""

import os

from subprocess import SubprocessError

from gi.repository import GLib

from gradience.backend.globals import is_sandboxed
from gradience.backend.utils.gsettings import GSettingsSetting, FlatpakGSettings, GSettingsMissingError
from gradience.backend.utils.subprocess import GradienceSubprocess
from gradience.backend.logger import Logger

logging = Logger()

INTERFACE_SCHEMA = "org.gnome.desktop.interface"
WM_SCHEMA = "org.gnome.desktop.wm.preferences"

USER_THEMES_DIR = os.path.join(GLib.get_home_dir(), ".local", "share", "themes")
USER_ICONS_DIR = os.path.join(GLib.get_home_dir(), ".local", "share", "icons")

BUTTON_LAYOUTS = [
    ("appmenu:close", "Close only (GNOME default)"),
    ("appmenu:minimize,maximize,close", "Minimize, maximize, close"),
    ("close,maximize,minimize:appmenu", "Left side (macOS-like)"),
    ("close:appmenu", "Close only, left side"),
]


def _settings(schema):
    retriever = FlatpakGSettings if is_sandboxed() else GSettingsSetting
    return retriever(schema)


def _get(settings, key):
    try:
        value = settings.get(key)
    except AttributeError:
        return settings.get_string(key)
    return str(value).strip().strip("'\"")


def _set(settings, key, value):
    try:
        settings.set(key, value)
    except AttributeError:
        settings.set_string(key, value)


def _host_listdir(path):
    """List a host directory even from inside the sandbox."""
    if not is_sandboxed():
        try:
            return sorted(os.listdir(path))
        except OSError:
            return []
    try:
        completed = GradienceSubprocess().run(
            ["ls", "-1", path], allow_escaping=True)
        out = GradienceSubprocess().get_stdout_data(completed, decode=True)
    except (SubprocessError, OSError):
        return []
    # A host `ls` cannot cheaply distinguish files from theme directories;
    # drop anything that looks like a file so stray SVGs or caches in the
    # system dirs never appear as selectable themes.
    return sorted(
        line for line in out.splitlines()
        if line and not line.lower().endswith(
            (".svg", ".png", ".jpg", ".theme", ".cache", ".txt", ".md")))


class DesktopSettings:
    """Read and set the appearance keys, and enumerate what they can name."""

    def __init__(self):
        self.interface = _settings(INTERFACE_SCHEMA)
        self.wm = _settings(WM_SCHEMA)

    # -- enumeration -----------------------------------------------------

    def gtk3_themes(self) -> list:
        """Theme names providing gtk-3.0, host and user dirs merged."""
        names = set()
        for name in _host_listdir("/usr/share/themes"):
            names.add(name)
        try:
            for name in os.listdir(USER_THEMES_DIR):
                if os.path.isdir(os.path.join(USER_THEMES_DIR, name, "gtk-3.0")):
                    names.add(name)
        except OSError:
            pass
        # Host listing can't cheaply check subdirs; keep every host name and
        # let the extension check speak to whether sandboxed apps resolve it.
        names.add("Adwaita")
        return sorted(names, key=str.casefold)

    def cursor_themes(self) -> list:
        names = set()
        for base in ("/usr/share/icons",):
            for name in _host_listdir(base):
                names.add(name)
        try:
            for name in os.listdir(USER_ICONS_DIR):
                if os.path.isdir(os.path.join(USER_ICONS_DIR, name, "cursors")):
                    names.add(name)
        except OSError:
            pass
        names.add("Adwaita")
        return sorted(names, key=str.casefold)

    def gtk3_extension_missing(self, theme_name: str) -> bool:
        """True when no org.gtk.Gtk3theme.<name> extension is installed —
        the case where sandboxed apps silently fall back to Adwaita."""
        if theme_name in ("Adwaita", "HighContrast", "HighContrastInverse"):
            return False        # built into GTK itself, resolves everywhere
        try:
            completed = GradienceSubprocess().run(
                ["flatpak", "list", "--runtime", "--columns=application"],
                allow_escaping=True)
            out = GradienceSubprocess().get_stdout_data(completed, decode=True)
        except (SubprocessError, OSError) as e:
            logging.warning(f"Could not query Flatpak runtimes: {e}")
            return False        # unknown — do not cry wolf
        return f"org.gtk.Gtk3theme.{theme_name}" not in out

    # -- keys ------------------------------------------------------------

    def get_gtk_theme(self) -> str:
        return _get(self.interface, "gtk-theme")

    def set_gtk_theme(self, name: str) -> None:
        _set(self.interface, "gtk-theme", name)

    def get_cursor_theme(self) -> str:
        return _get(self.interface, "cursor-theme")

    def set_cursor_theme(self, name: str) -> None:
        _set(self.interface, "cursor-theme", name)

    def get_color_scheme(self) -> str:
        return _get(self.interface, "color-scheme")

    def set_color_scheme(self, scheme: str) -> None:
        _set(self.interface, "color-scheme", scheme)

    def get_button_layout(self) -> str:
        return _get(self.wm, "button-layout")

    def set_button_layout(self, layout: str) -> None:
        _set(self.wm, "button-layout", layout)
