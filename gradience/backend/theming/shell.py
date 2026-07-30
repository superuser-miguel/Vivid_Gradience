# shell.py
#
# Change the look of Adwaita, with ease
# Copyright (C) 2023, Gradience Team
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

"""GNOME Shell theming.

This used to vendor GNOME's own Shell stylesheet sources, one copy per release,
and compile them with libsass. That is why it stopped at GNOME 45: every Shell
release meant porting a new SCSS tree, and a version that had not been vendored
was simply refused.

This rethemes the stylesheet the installed Shell already ships instead. The
Shell's own CSS is pulled out of its GResource, its colours are remapped onto
the preset's surfaces by luminance, and the result is written back out as a
user theme. Nothing here knows or cares which Shell version it is running
against, which is the entire point -- on GNOME 50 that file is ~3,300 lines
holding 51 distinct colours, and none of them need naming in advance.

Two things make this work:

- The Shell parameterises its own stylesheet on ``-st-accent-color`` and
  ``-st-accent-fg-color``, which are read-only, resolved from the nine-value
  ``org.gnome.desktop.interface accent-color`` enum. They cannot be assigned --
  but a *generated* stylesheet can substitute literals for them, and the
  Shell's own ``st-mix()`` / ``st-lighten()`` / ``st-darken()`` derivations keep
  working on whatever they are replaced with. That escapes the enum entirely.

- ``Main.setThemeStylesheet()``, which the User Themes extension calls when its
  setting changes, restyles a **running** Shell. Applying a Shell theme takes
  effect immediately; no logout, no restart.

The GResource belongs to the host, not to our runtime, so reading it goes
through ``flatpak-spawn --host`` -- the same escape ``get_shell_version()``
already uses. No additional sandbox permission is required.
"""

import os
import re
import os.path
import shutil

from gi.repository import GObject, Gio, GLib

from gradience.backend.models.preset import Preset
from gradience.backend.utils.colors import color_vars_to_color_code
from gradience.backend.utils.gnome import get_shell_version, get_shell_colors
from gradience.backend.utils.subprocess import GradienceSubprocess
from gradience.backend.utils.gsettings import GSettingsSetting, FlatpakGSettings, GSettingsMissingError

from gradience.backend.logger import Logger
from gradience.backend.exceptions import UnsupportedShellVersion
from gradience.backend.globals import is_sandboxed

logging = Logger(logger_name="ShellTheme")


SHELL_GRESOURCE = "/usr/share/gnome-shell/gnome-shell-theme.gresource"
SHELL_CSS_PATH = "/org/gnome/shell/theme/gnome-shell-{variant}.css"

# A six-digit hex not immediately followed by a rule opening -- the negative
# lookahead keeps a six-character hexadecimal id selector from being mistaken
# for a colour. No such selector exists in the shipped stylesheet, but a
# generated file should not depend on that staying true.
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\b(?!\s*\{)")


def _rgb(color: str) -> tuple:
    color = color.lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    return tuple(int(color[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _hex(rgb: tuple) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02x}" for c in rgb)


def _luminance(color: str) -> float:
    def linear(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (linear(c) for c in _rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _mix(a: str, b: str, t: float) -> str:
    x, y = _rgb(a), _rgb(b)
    return _hex(tuple(x[i] + (y[i] - x[i]) * t for i in range(3)))


class ShellTheme:
    theme_variant = None

    shell_colors = {}
    preset_variables = {}
    preset_palette = {}

    custom_css = None

    def __init__(self, shell_version=None):
        self._cancellable = Gio.Cancellable()

        # Kept for reporting only. Support is no longer decided by a list of
        # known versions -- it is decided by whether the installed Shell's
        # stylesheet can actually be read, which is checked when a theme is
        # generated.
        self.version_target = shell_version or self._detect_shell_version()

        self.THEME_GSETTINGS_SCHEMA_ID = "org.gnome.shell.extensions.user-theme"
        self.THEME_GSETTINGS_SCHEMA_PATH = "/org/gnome/shell/extensions/user-theme/"
        self.THEME_GSETTINGS_SCHEMA_KEY = "name"

        self.THEME_EXT_NAME = "user-theme@gnome-shell-extensions.gcampax.github.com"
        self.THEME_GSETTINGS_DIR = os.path.join(GLib.get_home_dir(), ".local/share/",
            "gnome-shell", "extensions", self.THEME_EXT_NAME, "schemas")

        try:
            settings_retriever = FlatpakGSettings if is_sandboxed() else GSettingsSetting
            schema_dir = self.THEME_GSETTINGS_DIR if os.path.exists(self.THEME_GSETTINGS_DIR) else None
            self.settings = settings_retriever(self.THEME_GSETTINGS_SCHEMA_ID, schema_dir=schema_dir)
        except (GSettingsMissingError, GLib.GError):
            raise

        self.theme_name = "VividGradience"
        self.output_dir = os.path.join(
            GLib.get_home_dir(), ".local/share/themes", self.theme_name, "gnome-shell")

    def get_cancellable(self) -> Gio.Cancellable:
        return self._cancellable

    def apply_theme_async(self, caller:GObject.Object, callback:callable,
                            theme_variant:str,
                            preset: Preset):
        task = Gio.Task.new(caller, None, callback, self._cancellable)
        self.async_data = (theme_variant, preset)

        task.set_return_on_cancel(True)
        task.run_in_thread(self._apply_theme_thread)

    def _apply_theme_thread(self, task:Gio.Task, source_object:GObject.Object,
                                task_data:object,
                                cancellable:Gio.Cancellable):
        if task.return_error_if_cancelled():
            return

        theme_variant, preset = self.async_data

        output = self.apply_theme(source_object, theme_variant, preset)
        task.return_value(output)

    # TODO: Make it accept either dict or callable in `parent` parameter
    def apply_theme(self, parent: callable, theme_variant: str, preset: Preset):
        if theme_variant in ("light", "dark"):
            self.theme_variant = theme_variant
        else:
            raise ValueError(
                f"Theme variant {theme_variant} not in list: [light, dark]")

        try:
            self._create_theme(parent, preset)
        except (OSError, GLib.GError):
            raise

    def _create_theme(self, parent: callable, preset: Preset):
        # Convert GTK color variables to normal color values
        self.preset_variables = color_vars_to_color_code(preset.variables, preset.palette)
        self.preset_palette = preset.palette
        self.custom_css = preset.custom_css

        parent_colors = getattr(parent, "shell_colors", None) if parent is not None else None
        self.shell_colors = parent_colors or get_shell_colors(self.preset_variables)

        stylesheet = self._recolor(self._read_shell_css(self.theme_variant))

        os.makedirs(self.output_dir, exist_ok=True)
        with open(os.path.join(self.output_dir, "gnome-shell.css"), "w",
                  encoding="utf-8") as sheet:
            sheet.write(stylesheet)

        self._set_shell_theme()

    def _read_shell_css(self, variant: str) -> str:
        """Pull the installed Shell's own stylesheet out of its GResource.

        The GResource is a host file; our runtime does not ship gnome-shell. The
        subprocess wrapper escapes the sandbox when it needs to, exactly as the
        version check does.
        """
        cmd_list = ["gresource", "extract", SHELL_GRESOURCE,
                    SHELL_CSS_PATH.format(variant=variant)]

        process = GradienceSubprocess()
        try:
            completed = process.run(cmd_list, allow_escaping=True)
            stylesheet = process.get_stdout_data(completed, decode=True)
        except (OSError, GLib.GError, Exception) as e:
            raise UnsupportedShellVersion(
                f"Could not read the GNOME Shell stylesheet from {SHELL_GRESOURCE}. "
                f"GNOME Shell {self.version_target or 'unknown'} may store it "
                f"elsewhere, or gnome-shell may not be installed."
            ) from e

        if not stylesheet or "{" not in stylesheet:
            raise UnsupportedShellVersion(
                f"The GNOME Shell stylesheet for the '{variant}' variant was "
                f"empty or unreadable (GNOME Shell {self.version_target or 'unknown'})."
            )

        return stylesheet

    def _resolve(self, value: str, over: str, depth: int = 0) -> str:
        """Reduce a preset value to a plain hex colour.

        Preset values are not all hex. A foreground is very often
        ``rgba(0, 0, 0, 0.8)``, and variables may point at each other with
        ``@references``. Treating those as unusable and falling back to a
        default silently inverts the curve -- light Adwaita took ``#ffffff`` as
        its foreground and rendered the whole Shell mid-grey.
        """
        if not isinstance(value, str) or depth > 8:
            return over
        value = value.strip()
        if value.startswith("@"):
            return self._resolve(self.preset_variables.get(value[1:]), over, depth + 1)
        if value.startswith("#"):
            return value if len(value) == 7 else _hex(_rgb(value))

        match = re.match(r"rgba?\(([^)]*)\)", value)
        if match:
            parts = [p.strip() for p in match.group(1).replace("/", ",").split(",")]
            if len(parts) >= 3:
                try:
                    fg = [float(p) / 255 for p in parts[:3]]
                    alpha = float(parts[3]) if len(parts) > 3 else 1.0
                except ValueError:
                    return over
                bg = _rgb(over)
                return _hex(tuple(fg[i] * alpha + bg[i] * (1 - alpha) for i in range(3)))
        return over

    def _build_curve(self) -> list:
        """Anchor points mapping Shell greys onto the preset's own surfaces.

        The Shell's stylesheet is built from a handful of surface tones and
        their tints. Anchoring on the surfaces and interpolating between them
        preserves the light-to-dark ordering that made the original read as
        depth, instead of flattening everything to one colour.
        """
        colors = self.shell_colors
        variables = self.preset_variables

        def pick(*names, over, fallback):
            for name in names:
                raw = colors.get(name) or variables.get(name)
                if raw:
                    resolved = self._resolve(raw, over)
                    if resolved:
                        return resolved
            return fallback

        background = pick("bg_color", "window_bg_color",
                          over="#222226", fallback="#222226")
        # Foregrounds composite over the background, which is what makes an
        # rgba() text colour resolve to the shade it actually appears as.
        foreground = pick("fg_color", "window_fg_color",
                          over=background, fallback="#ffffff")
        system = pick("system_bg_color", over=background, fallback=background)
        view = pick("view_bg_color", over=background, fallback=background)

        anchors = {_luminance(c): c for c in (background, foreground, system, view)}
        points = sorted(anchors.items())
        if len(points) < 2:  # a scheme with no tonal range to interpolate across
            points = [(0.0, background), (1.0, foreground)]

        # Extend past both ends so the Shell's highlights and shadows keep their
        # range instead of clamping onto the outermost surface.
        darkest, lightest = points[0][1], points[-1][1]
        return ([(0.0, _mix(darkest, "#000000", 0.5))] + points
                + [(1.0, _mix(lightest, "#ffffff", 0.5))])

    def _remap(self, color: str, curve: list) -> str:
        target = _luminance(color)
        for i in range(len(curve) - 1):
            (low, low_color), (high, high_color) = curve[i], curve[i + 1]
            if low <= target <= high:
                t = 0.0 if high == low else (target - low) / (high - low)
                return _mix(low_color, high_color, t)
        return curve[-1][1] if target > curve[-1][0] else curve[0][1]

    def _recolor(self, stylesheet: str) -> str:
        curve = self._build_curve()
        colors = self.shell_colors
        seen = {}

        def substitute(match):
            found = match.group(0).lower()
            if found not in seen:
                seen[found] = self._remap(found, curve)
            return seen[found]

        out = HEX_COLOR.sub(substitute, stylesheet)

        # The accent keywords are resolved from a nine-value enum and cannot be
        # assigned. Replacing them with literals sidesteps that; the Shell's own
        # colour functions still operate on the substituted value.
        accent_bg = self._resolve(
            colors.get("selected_bg_color")
            or self.preset_variables.get("accent_bg_color"), "#3584e4")
        accent_fg = self._resolve(
            colors.get("selected_fg_color")
            or self.preset_variables.get("accent_fg_color"), accent_bg)
        out = out.replace("-st-accent-fg-color", accent_fg)
        out = out.replace("-st-accent-color", accent_bg)

        # The panel is not special-cased: the Shell's own `#panel` rule is
        # remapped along with everything else, which keeps it in step with the
        # surfaces around it.

        shell_css = (self.custom_css or {}).get("shell", "")
        if shell_css:
            out += f"\n\n/* Custom CSS */\n{shell_css}\n"

        logging.debug(f"Recolored {len(seen)} colors in the Shell stylesheet.")
        return out

    def _set_shell_theme(self):
        key = self.THEME_GSETTINGS_SCHEMA_KEY

        # The extension only reacts to a *change* of this key, so re-applying
        # the same theme has to clear it first or nothing reloads.
        self.settings.reset(key)

        if is_sandboxed():
            self.settings.set(key, self.theme_name)
        else:
            self.settings.set_string(key, self.theme_name)

    def _detect_shell_version(self):
        try:
            shell_version = get_shell_version()
        except Exception:
            return None

        if shell_version and shell_version.startswith("3"):
            raise UnsupportedShellVersion(
                f"GNOME Shell version {shell_version} is not supported. "
                f"Shell theming requires GNOME 40 or later."
            )

        return shell_version

    def reset_theme_async(self, caller:GObject.Object, callback:callable):
        task = Gio.Task.new(caller, None, callback, self._cancellable)

        task.set_return_on_cancel(True)
        task.run_in_thread(self._reset_theme_thread)

    def reset_theme(self):
        key = self.THEME_GSETTINGS_SCHEMA_KEY

        # Set default theme
        self.settings.reset(key)

        # Also delete what we generated — resetting only the key leaves a
        # stale stylesheet under ~/.local/share/themes that the next session
        # of the User Themes extension could still pick from its list.
        if os.path.isdir(self.output_dir):
            shutil.rmtree(self.output_dir, ignore_errors=True)
            parent = os.path.dirname(self.output_dir)
            try:
                os.rmdir(parent)  # only removes it when nothing else is left
            except OSError:
                pass

    def _reset_theme_thread(self, task:Gio.Task, source_object:GObject.Object,
                task_data:object, cancellable:Gio.Cancellable):
        if task.return_error_if_cancelled():
            return

        output = self.reset_theme()
        task.return_value(output)
