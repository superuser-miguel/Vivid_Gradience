# theme_preview.py
#
# Change the look of Adwaita, with ease
# Copyright (C) 2022-2023, Gradience Team
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

"""A schematic, live preview of the preset being edited.

Why drawn rather than composed from real widgets: libadwaita only picks up
named-colour overrides from the stylesheet it loads at startup. A CSS provider
added at runtime has no effect on them, at any priority, so a strip of real
GTK widgets inside this process would keep showing the theme the app launched
with — not the one being edited.

Drawing it also means the preview knows the colours it is painting, so it can
mark the pairs that fall below WCAG AA in place, rather than reporting them
somewhere else.

Deliberately schematic. It reads as a diagram of a window, not as a screenshot,
which keeps it honest about being an approximation and avoids chasing Adwaita's
exact chrome for ever.
"""

import math

from gi.repository import Gtk, Gdk, Pango, PangoCairo

AA = 4.5

# (foreground, background, what to call it if it fails)
CHECKED_PAIRS = [
    ("window_fg_color", "window_bg_color", "window text"),
    ("headerbar_fg_color", "headerbar_bg_color", "header bar"),
    ("sidebar_fg_color", "sidebar_bg_color", "sidebar"),
    ("card_fg_color", "card_bg_color", "card"),
    ("accent_fg_color", "accent_bg_color", "accent button"),
    ("success_fg_color", "success_bg_color", "success"),
    ("warning_fg_color", "warning_bg_color", "warning"),
    ("error_fg_color", "error_bg_color", "error"),
]

FALLBACK = (0.5, 0.5, 0.5)


def _rgba(value):
    rgba = Gdk.RGBA()
    return rgba if value and rgba.parse(value) else None


def resolve(variables, name, over=None, depth=0):
    """A variable as an opaque (r, g, b), following @references.

    `over` is whatever sits behind it, needed because a translucent value has
    no real colour on its own — Adwaita Dark's card is rgba(255,255,255,0.08).
    """
    if depth > 8:
        return None
    value = variables.get(name)
    if not value:
        return None
    value = value.strip()
    if value.startswith("@"):
        return resolve(variables, value[1:], over, depth + 1)
    rgba = _rgba(value)
    if rgba is None:
        return None
    if rgba.alpha >= 1.0:
        return (rgba.red, rgba.green, rgba.blue)
    back = over or (0, 0, 0)
    return tuple(c * rgba.alpha + b * (1 - rgba.alpha)
                 for c, b in zip((rgba.red, rgba.green, rgba.blue), back))


def _luminance(rgb):
    def channel(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a, b):
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def failing_pairs(variables):
    """Every checked pair below AA, worst first."""
    out = []
    window = resolve(variables, "window_bg_color")
    for fg_key, bg_key, label in CHECKED_PAIRS:
        bg = resolve(variables, bg_key, over=window)
        if bg is None:
            continue
        fg = resolve(variables, fg_key, over=bg)
        if fg is None:
            continue
        ratio = contrast(fg, bg)
        if ratio < AA:
            out.append((ratio, label))
    return sorted(out)


def _rounded(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.close_path()


def _text(cr, layout, x, y, text, rgb, size=10, bold=False):
    desc = Pango.FontDescription("sans")
    desc.set_size(int(size * Pango.SCALE))
    desc.set_weight(Pango.Weight.BOLD if bold else Pango.Weight.NORMAL)
    layout.set_font_description(desc)
    layout.set_text(text, -1)
    cr.set_source_rgb(*rgb)
    cr.move_to(x, y)
    PangoCairo.show_layout(cr, layout)


def _warn_badge(cr, x, y):
    """An amber triangle marking a region whose text is below AA."""
    r = 7
    cr.move_to(x, y - r)
    cr.line_to(x + r, y + r * 0.7)
    cr.line_to(x - r, y + r * 0.7)
    cr.close_path()
    cr.set_source_rgb(0.96, 0.76, 0.06)
    cr.fill_preserve()
    cr.set_source_rgba(0, 0, 0, 0.55)
    cr.set_line_width(1)
    cr.stroke()
    cr.set_source_rgb(0.15, 0.12, 0)
    cr.rectangle(x - 0.8, y - r * 0.45, 1.6, r * 0.75)
    cr.fill()
    cr.rectangle(x - 0.8, y + r * 0.42, 1.6, 1.6)
    cr.fill()


def draw(cr, width, height, variables):
    """Paint the schematic. Pure cairo, so it is testable without a window."""
    def colour(name, over=None):
        return resolve(variables, name, over=over) or FALLBACK

    window = colour("window_bg_color")
    header = colour("headerbar_bg_color", over=window)
    sidebar = colour("sidebar_bg_color", over=window)
    card = colour("card_bg_color", over=window)
    accent = colour("accent_bg_color", over=window)

    failing = {label for _, label in failing_pairs(variables)}
    layout = PangoCairo.create_layout(cr)

    pad = 6
    x, y = pad, pad
    w, h = width - pad * 2, height - pad * 2
    header_h = 26
    side_w = min(96, w * 0.3)

    cr.save()
    _rounded(cr, x, y, w, h, 9)
    cr.clip()

    cr.set_source_rgb(*window)
    cr.paint()
    cr.rectangle(x, y, w, header_h)
    cr.set_source_rgb(*header)
    cr.fill()
    cr.rectangle(x, y + header_h, side_w, h - header_h)
    cr.set_source_rgb(*sidebar)
    cr.fill()

    _text(cr, layout, x + 10, y + 6, "Preview", colour("headerbar_fg_color", header),
          10, True)
    side_fg = colour("sidebar_fg_color", sidebar)
    for i, item in enumerate(("Colors", "Theming", "Presets")):
        _text(cr, layout, x + 10, y + header_h + 8 + i * 16, item, side_fg, 9)

    cx = x + side_w + 12
    cw = w - side_w - 24
    _rounded(cr, cx, y + header_h + 10, cw, 54, 7)
    cr.set_source_rgb(*card)
    cr.fill()
    card_fg = colour("card_fg_color", card)
    _text(cr, layout, cx + 10, y + header_h + 16, "Card surface", card_fg, 10, True)
    _text(cr, layout, cx + 10, y + header_h + 34, "body text", card_fg, 9)

    btn_y = y + header_h + 76
    _rounded(cr, cx, btn_y, 74, 24, 6)
    cr.set_source_rgb(*accent)
    cr.fill()
    _text(cr, layout, cx + 16, btn_y + 4, "Apply",
          colour("accent_fg_color", accent), 9, True)

    dot_x = cx + 92
    for key, label in (("success_bg_color", "success"),
                       ("warning_bg_color", "warning"),
                       ("error_bg_color", "error")):
        cr.arc(dot_x, btn_y + 12, 7, 0, 2 * math.pi)
        cr.set_source_rgb(*colour(key, window))
        cr.fill()
        if label in failing:
            _warn_badge(cr, dot_x + 9, btn_y + 3)
        dot_x += 26

    if "window text" in failing:
        _warn_badge(cr, x + w - 14, y + h - 14)
    if "header bar" in failing:
        _warn_badge(cr, x + w - 14, y + 12)
    if "sidebar" in failing:
        _warn_badge(cr, x + side_w - 12, y + h - 14)
    if "card" in failing:
        _warn_badge(cr, cx + cw - 12, y + header_h + 20)
    if "accent button" in failing:
        _warn_badge(cr, cx + 66, btn_y + 4)

    cr.restore()

    _rounded(cr, x, y, w, h, 9)
    cr.set_source_rgba(0, 0, 0, 0.22)
    cr.set_line_width(1)
    cr.stroke()


class GradienceThemePreview(Gtk.DrawingArea):
    """Live schematic of the preset being edited."""

    __gtype_name__ = "GradienceThemePreview"

    def __init__(self, get_variables, **kwargs):
        super().__init__(**kwargs)
        self._get_variables = get_variables
        self.set_content_height(160)
        self.set_draw_func(self._on_draw)

    def _on_draw(self, _area, cr, width, height):
        variables = self._get_variables() or {}
        if variables:
            draw(cr, width, height, variables)

    def refresh(self):
        self.queue_draw()
