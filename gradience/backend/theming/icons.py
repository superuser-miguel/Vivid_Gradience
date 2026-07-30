# icons.py
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

"""Recoloured "pseudo-Adwaita" icon theme, generated from a preset.

Adwaita's folder icons are blue because the blue is written into the SVGs; no
colour variable reaches them. This engine rewrites just the blue-bearing icons
through a luminance curve built from one of the preset's palette ramps and
writes them as a small theme that inherits everything else from Adwaita.
Port of tools/icons-from-preset.py, which remains the scriptable form.
"""

import colorsys
import os
import re
import shutil

from gi.repository import GLib

from gradience.backend.utils.gsettings import GSettingsSetting, FlatpakGSettings, GSettingsMissingError
from gradience.backend.globals import is_sandboxed
from gradience.backend.logger import Logger

logging = Logger()

ADWAITA = "/usr/share/icons/Adwaita"
CONTEXTS = {"places": "Places", "devices": "Devices",
            "mimetypes": "MimeTypes", "status": "Status"}
# Below this, a folder stops reading as a folder against the view behind it.
MIN_VISIBLE = 1.9
BLUE_HUE = (195, 250)
BLUE_MIN_SAT = 0.25
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")

NEUTRAL_RAMPS = ("light_", "dark_")
# The folder's main body -- the most-used blue in the whole icon set. Ramps
# are scored by what THIS becomes, not by a shade picked out of the ramp.
FOLDER_BODY = "#62a0ea"


def _rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _lum(h):
    def f(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b):
    x, y = sorted((_lum(a), _lum(b)))
    return (y + 0.05) / (x + 0.05)


def _hue(h):
    return colorsys.rgb_to_hls(*_rgb(h))[0] * 360


def _hue_gap(a, b):
    d = abs(_hue(a) - _hue(b)) % 360
    return min(d, 360 - d)


def _flatten(variables, name, over, depth=0):
    """Resolve @references and composite rgba() over a known background."""
    c = variables.get(name, over)
    if depth > 8:
        return over
    if isinstance(c, str) and c.startswith("@"):
        return _flatten(variables, c[1:], over, depth + 1)
    m = re.match(r"rgba?\(([^)]*)\)", c or "")
    if m:
        p = [x.strip() for x in m.group(1).split(",")]
        if len(p) >= 3:
            fg = [float(x) / 255 for x in p[:3]]
            a = float(p[3]) if len(p) > 3 else 1.0
            bg = _rgb(over)
            return "#" + "".join(
                f"{round(255 * (fg[i] * a + bg[i] * (1 - a))):02x}" for i in range(3))
    return c if isinstance(c, str) and c.startswith("#") else over


def _is_blue(h):
    hh, _, s = colorsys.rgb_to_hls(*_rgb(h))
    return BLUE_HUE[0] <= hh * 360 <= BLUE_HUE[1] and s >= BLUE_MIN_SAT


def _affected_icons():
    """Every full-colour Adwaita SVG containing a blue, with its blues."""
    found = []
    root = os.path.join(ADWAITA, "scalable")
    for dirpath, _, files in os.walk(root):
        for f in sorted(files):
            if not f.endswith(".svg") or "symbolic" in f:
                continue
            p = os.path.join(dirpath, f)
            try:
                data = open(os.path.realpath(p), encoding="utf-8").read()
            except OSError:
                continue
            blues = {h.lower() for h in HEX.findall(data) if _is_blue(h)}
            if blues:
                found.append((os.path.relpath(p, root), data, blues))
    return sorted(found)


def _make_curve(shades):
    """A luminance -> colour curve from a ramp, extended past both ends."""
    pts = sorted(((_lum(s), s) for s in shades), key=lambda t: t[0])
    lightest, darkest = pts[-1][1], pts[0][1]

    def mix(a, b, t):
        x, y = _rgb(a), _rgb(b)
        return "#" + "".join(
            f"{round(255 * (x[i] + (y[i] - x[i]) * t)):02x}" for i in range(3))

    # Keep the family's hue at the extremes rather than fading to pure grey.
    top, bottom = mix(lightest, "#ffffff", 0.75), mix(darkest, "#000000", 0.6)
    return [(0.0, bottom)] + pts + [(1.0, top)]


def _remap(h, curve):
    L = _lum(h)
    for i in range(len(curve) - 1):
        (l0, c0), (l1, c1) = curve[i], curve[i + 1]
        if l0 <= L <= l1:
            t = 0.0 if l1 == l0 else (L - l0) / (l1 - l0)
            a, b = _rgb(c0), _rgb(c1)
            return "#" + "".join(
                f"{round(255 * (a[j] + (b[j] - a[j]) * t)):02x}" for j in range(3))
    return curve[-1][1] if L > curve[-1][0] else curve[0][1]


class IconTheme:
    """Generate, select and remove the recoloured icon theme."""

    ICON_GSETTINGS_SCHEMA_ID = "org.gnome.desktop.interface"
    ICON_GSETTINGS_KEY = "icon-theme"

    def __init__(self):
        self.theme_name = "VividGradience"
        self.output_dir = os.path.join(
            GLib.get_home_dir(), ".local/share/icons", self.theme_name)

        settings_retriever = FlatpakGSettings if is_sandboxed() else GSettingsSetting
        try:
            self.settings = settings_retriever(self.ICON_GSETTINGS_SCHEMA_ID)
        except (GSettingsMissingError, GLib.GError):
            raise

    # -- scoring ---------------------------------------------------------

    def score_ramps(self, preset):
        """Rank the palette ramps by what the folder actually becomes."""
        variables, palette = preset.variables, preset.palette or {}
        view = _flatten(variables, "view_bg_color", "#ffffff")
        accent = _flatten(variables, "accent_bg_color", "#3584e4")

        # A near-neutral accent has no hue to match against; measured as
        # chroma, not HLS saturation, which reads dark-but-coloured as grey.
        r_, g_, b_ = _rgb(accent)
        monochrome = (max(r_, g_, b_) - min(r_, g_, b_)) < 0.05

        rows = []
        for name, shades in palette.items():
            try:
                curve = _make_curve([shades[str(i)] for i in range(1, 6)])
            except (KeyError, ValueError):
                continue
            body = _remap(FOLDER_BODY, curve)
            rows.append({
                "ramp": name,
                "body": body,
                "contrast": _contrast(body, view),
                "hue_gap": _hue_gap(body, accent),
                "neutral": name in NEUTRAL_RAMPS,
            })

        def visible(rs):
            return [r for r in rs if r["contrast"] >= MIN_VISIBLE]

        chromatic = [r for r in rows if not r["neutral"]]
        pool_is_chromatic = bool(visible(chromatic)) and not monochrome
        # Decided before sorting: list.sort() empties the list while it runs,
        # so a check against `rows` inside the key would always see [].
        rank_by_contrast = monochrome or not visible(rows)

        def key(r):
            return (
                r["neutral"] if pool_is_chromatic else False,
                r["contrast"] < MIN_VISIBLE,
                -r["contrast"] if rank_by_contrast else r["hue_gap"],
            )

        rows.sort(key=key)
        return rows, view, accent

    def choice(self, preset):
        """The ramp Apply would use, with the reason — for display."""
        rows, _view, _accent = self.score_ramps(preset)
        if not rows:
            return None
        chosen = rows[0]
        chosen = dict(chosen)
        chosen["why"] = (
            _("nearest the accent") if chosen["contrast"] >= MIN_VISIBLE
            else _("most visible ramp available"))
        return chosen

    # -- generation ------------------------------------------------------

    def generate(self, preset, ramp=None):
        """Write the theme dir. Returns (chosen_row, n_colours, n_files)."""
        rows, _view, _accent = self.score_ramps(preset)
        if not rows:
            raise ValueError("preset has no usable palette ramps")

        if ramp is not None:
            match = [r for r in rows if r["ramp"] == ramp]
            if not match:
                raise ValueError(f"no ramp {ramp!r} in this preset")
            chosen = match[0]
        else:
            chosen = rows[0]

        icons = _affected_icons()
        if not icons:
            raise OSError(f"no recolourable icons found under {ADWAITA}/scalable")

        shades = [preset.palette[chosen["ramp"]][str(i)] for i in range(1, 6)]
        curve = _make_curve(shades)

        mapping = {}
        for _rel, _data, blues in icons:
            for b in blues:
                mapping.setdefault(b, _remap(b, curve))

        if os.path.isdir(self.output_dir):
            shutil.rmtree(self.output_dir)

        contexts = {}
        for rel, data, _blues in icons:
            sub = os.path.dirname(rel)
            contexts.setdefault(sub, CONTEXTS.get(os.path.basename(sub), "Places"))
            dest = os.path.join(self.output_dir, "scalable", rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            out = HEX.sub(lambda m: mapping.get(m.group(0).lower(), m.group(0)), data)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(out)

        preset_name = getattr(preset, "display_name", None) or "preset"
        dirs = sorted(contexts)
        index = [
            "[Icon Theme]",
            f"Name={self.theme_name}",
            f"Comment=Adwaita recoloured to match the {preset_name} scheme",
            # Inheriting is what keeps this a small theme instead of a fork:
            # anything not recoloured falls through to Adwaita itself.
            "Inherits=Adwaita",
            "Directories=" + ",".join(f"scalable/{d}" for d in dirs),
            "",
        ]
        for d in dirs:
            index += [f"[scalable/{d}]", "Size=128", "MinSize=8", "MaxSize=512",
                      f"Context={contexts[d]}", "Type=Scalable", ""]
        with open(os.path.join(self.output_dir, "index.theme"), "w") as f:
            f.write("\n".join(index))

        # The derivation is licence-compatible only with attribution shipped
        # alongside — this file is not optional.
        with open(os.path.join(self.output_dir, "COPYING-Adwaita"), "w") as f:
            f.write(
                "The icons in this theme are derived from the Adwaita icon theme,\n"
                "recoloured but otherwise unmodified.\n\n"
                "Adwaita icon theme, Copyright the GNOME Project.\n"
                "Licensed LGPL-3.0-only OR CC-BY-SA-3.0.\n"
                "https://gitlab.gnome.org/GNOME/adwaita-icon-theme\n\n"
                "This derived theme is distributed under the same terms.\n")

        logging.debug(
            f"Icon theme written to {self.output_dir}: ramp {chosen['ramp']}, "
            f"{len(mapping)} colours, {len(icons)} icons")
        return chosen, len(mapping), len(icons)

    # -- selection -------------------------------------------------------

    def current_theme(self) -> str:
        try:
            value = self.settings.get(self.ICON_GSETTINGS_KEY)
        except AttributeError:
            return self.settings.get_string(self.ICON_GSETTINGS_KEY)
        return str(value).strip().strip("'\"")

    def apply(self, preset, ramp=None):
        result = self.generate(preset, ramp)
        try:
            self.settings.set(self.ICON_GSETTINGS_KEY, self.theme_name)
        except AttributeError:
            self.settings.set_string(self.ICON_GSETTINGS_KEY, self.theme_name)
        return result

    def remove(self):
        """Point the desktop back at its default and delete our directory.

        Only resets the key when it currently names our theme — if the user
        selected something else since, that choice is theirs to keep.
        """
        if self.current_theme() == self.theme_name:
            self.settings.reset(self.ICON_GSETTINGS_KEY)

        removed = False
        index = os.path.join(self.output_dir, "index.theme")
        if os.path.isdir(self.output_dir) and os.path.isfile(index):
            with open(index, "r", encoding="utf-8") as f:
                ours = f"Name={self.theme_name}" in f.read()
            if ours:
                shutil.rmtree(self.output_dir)
                removed = True
        return removed
