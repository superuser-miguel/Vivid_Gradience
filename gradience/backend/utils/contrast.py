# contrast.py
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

"""Choose text colours by measuring them, not by reading a name.

A preset names its colours by role, and the toolkit composes pairs from those
roles that the preset never wrote down: `destructive_color` drawn as a label
on a card, for one. Measured on the bundled presets, 247 of 425 such labels
fell below WCAG AA. FEAR's red "Reset Theme" sat at 1.11:1 on its own cards.

Settled 2026-10-07:

- The floor is 4.5:1 (WCAG AA for body text).
- A colour the preset wrote is kept whenever it already clears the floor.
  Presets are authored, and a passing colour is the author's choice.
- Coloured text keeps its hue, because the hue is the meaning (red means
  danger). Only its OKLCH lightness moves, by the smallest amount that clears
  the floor on every surface it is drawn on.
- Text on a filled surface (the accent button) that fails is replaced by the
  readable shade nearest in hue from the scheme's own palette. If the palette
  has none, the nearest one has its lightness moved instead.

The direction of a move is decided by measuring both, never by a luminance
threshold. The white/black crossover sits at luminance 0.179, not 0.5.

Pure Python, with no GTK imports, so tools/pick-foreground.py can load the
same code by path.
"""

import math
import re

FLOOR = 4.5

# Roles whose standalone colour is drawn as text on the neutral surfaces.
TEXT_ROLES = ("accent", "destructive", "success", "warning", "error")
TEXT_SURFACES = ("window_bg_color", "view_bg_color", "card_bg_color")
# Roles drawn as a filled surface carrying their own foreground.
FILL_ROLES = TEXT_ROLES

NAMED_FG = ("window_fg_color", "view_fg_color", "card_fg_color",
            "headerbar_fg_color", "popover_fg_color", "dialog_fg_color",
            "sidebar_fg_color", "accent_fg_color")

# Hue distances inside one band count as equal and contrast breaks the tie,
# so of two shades both in the background's family the more readable wins.
HUE_BAND = 15.0
# Below this OKLCH chroma a colour has no meaningful hue.
ACHROMATIC = 0.02
# Hue distance charged when exactly one side is achromatic: worse than a near
# neighbour, better than the opposite side of the wheel.
NEUTRAL_HUE_PENALTY = 60.0

_RGBA = re.compile(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)"
                   r"(?:\s*,\s*([\d.]+))?\s*\)")


# --- reading colours ---------------------------------------------------------

def flatten_palette(palette):
    """`{"blue_": {"1": "#…"}}` as `{"blue_1": "#…"}`, the names presets use
    when they refer to a shade (`@blue_1`)."""
    flat = {}
    for prefix, shades in (palette or {}).items():
        for key, value in shades.items():
            flat[prefix + key] = value
    return flat


def resolve(value, names, over=None, depth=0):
    """An (r, g, b) tuple for `value`, or None if it cannot be pinned down.

    `value` may be a hex colour, an `@reference` into `names`, or an rgba()
    that only has a real colour once composited over `over`.
    """
    if value is None or depth > 8:
        return None
    value = str(value).strip()
    if value.startswith("@"):
        return resolve(names.get(value[1:]), names, over, depth + 1)
    if value.startswith("#"):
        if len(value) == 7:
            return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
        if len(value) == 4:
            return tuple(int(ch * 2, 16) for ch in value[1:])
        return None
    m = _RGBA.match(value)
    if m:
        r, g, b = (float(m.group(i)) for i in (1, 2, 3))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        if a >= 1.0:
            return (r, g, b)
        if over is None:
            return None
        return tuple(c * a + o * (1 - a) for c, o in zip((r, g, b), over))
    return None


def to_hex(rgb):
    return "#%02x%02x%02x" % tuple(round(c) for c in rgb)


# --- WCAG contrast -----------------------------------------------------------

def luminance(rgb):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# --- OKLCH -------------------------------------------------------------------

def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c):
    c = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return c * 255


def to_oklch(rgb):
    r, g, b = (_lin(c) for c in rgb)
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def _from_oklab(L, a, b):
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
            -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
            -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)


def from_oklch(L, C, h):
    """sRGB for an OKLCH colour, shedding chroma until it fits the gamut."""
    hr = math.radians(h)
    for _ in range(40):
        lin = _from_oklab(L, C * math.cos(hr), C * math.sin(hr))
        if all(-1e-6 <= c <= 1 + 1e-6 for c in lin):
            break
        C *= 0.9
    return tuple(round(min(255, max(0, _gam(max(0.0, min(1.0, c))))))
                 for c in lin)


def hue_distance(a, b):
    (_, ca, ha), (_, cb, hb) = to_oklch(a), to_oklch(b)
    na, nb = ca < ACHROMATIC, cb < ACHROMATIC
    if na and nb:
        return 0.0
    if na or nb:
        return NEUTRAL_HUE_PENALTY
    d = abs(ha - hb) % 360
    return min(d, 360 - d)


# --- choosing ----------------------------------------------------------------

def push(rgb, surfaces, floor=FLOOR):
    """Move `rgb` along OKLCH lightness until it clears `floor` on every
    surface, by the smaller of the two possible moves.

    Returns (rgb, reached). When neither direction gets there, returns the
    end with the most contrast and reached=False.
    """
    L, C, h = to_oklch(rgb)

    def worst(colour):
        return min(contrast(colour, s) for s in surfaces)

    best = None
    for target in (1.0, 0.0):
        if worst(from_oklch(target, C, h)) < floor:
            continue
        lo, hi = L, target
        for _ in range(30):
            mid = (lo + hi) / 2
            if worst(from_oklch(mid, C, h)) >= floor:
                hi = mid
            else:
                lo = mid
        move = abs(hi - L)
        if best is None or move < best[0]:
            best = (move, from_oklch(hi, C, h))
    if best is None:
        ends = (from_oklch(1.0, C, h), from_oklch(0.0, C, h))
        return max(ends, key=worst), False
    return best[1], True


def candidates(variables, palette):
    """Every colour the scheme offers as text, as [(label, rgb)], unique."""
    names = dict(flatten_palette(palette))
    names.update(variables)
    base = resolve(variables.get("window_bg_color"), names)
    found, seen = [], set()
    entries = [(k.replace("_color", ""), variables.get(k)) for k in NAMED_FG]
    entries += sorted(flatten_palette(palette).items())
    for label, value in entries:
        rgb = resolve(value, names, over=base)
        if rgb is None:
            continue
        rgb = tuple(round(c) for c in rgb)
        if rgb not in seen:
            seen.add(rgb)
            found.append((label, rgb))
    return found


def pick(bg, cands, floor=FLOOR, mode="nearest-hue"):
    """The text colour for a filled surface `bg`.

    Returns (rgb, how, source) with how in {"picked", "pushed",
    "best-effort"}.
    """
    scored = [(label, rgb, contrast(rgb, bg), hue_distance(rgb, bg))
              for label, rgb in cands]
    if not scored:
        out, reached = push((255, 255, 255), [bg], floor)
        return out, "pushed" if reached else "best-effort", "white"
    clear = [s for s in scored if s[2] >= floor]
    if clear:
        if mode == "nearest-hue":
            label, rgb, _, _ = min(clear, key=lambda s: (s[3] // HUE_BAND, -s[2]))
        else:
            label, rgb, _, _ = max(clear, key=lambda s: s[2])
        return rgb, "picked", label
    if mode == "nearest-hue":
        label, rgb, _, _ = min(scored, key=lambda s: (s[3] // HUE_BAND, -s[2]))
    else:
        label, rgb, _, _ = max(scored, key=lambda s: s[2])
    out, reached = push(rgb, [bg], floor)
    return out, "pushed" if reached else "best-effort", label


def readable_variables(variables, palette=None, floor=FLOOR):
    """A copy of `variables` in which every role colour drawn as text reads.

    Returns (variables, changes). `changes` lists (name, old, new) for each
    value replaced; a value that already clears `floor` is left exactly as
    written, references and all.
    """
    out = dict(variables)
    changes = []
    names = dict(flatten_palette(palette))
    names.update(variables)
    base = resolve(variables.get("window_bg_color"), names)
    if base is None:
        return out, changes

    surfaces = [s for s in (resolve(variables.get(k), names, over=base)
                            for k in TEXT_SURFACES) if s is not None]

    # Coloured text: keep the hue, move the lightness.
    for role in TEXT_ROLES:
        key = f"{role}_color"
        col = resolve(variables.get(key), names, over=base)
        if col is None or not surfaces:
            continue
        if min(contrast(col, s) for s in surfaces) >= floor:
            continue
        new, _ = push(col, surfaces, floor)
        out[key] = to_hex(new)
        changes.append((key, variables.get(key), out[key]))

    # Text on fills: keep it if it reads, else the nearest-hue readable shade.
    cands = None
    for role in FILL_ROLES:
        bg = resolve(variables.get(f"{role}_bg_color"), names, over=base)
        key = f"{role}_fg_color"
        if bg is None or key not in variables:
            continue
        fg = resolve(variables.get(key), names, over=bg)
        if fg is not None and contrast(fg, bg) >= floor:
            continue
        if cands is None:
            cands = candidates(variables, palette)
        new, _, _ = pick(bg, cands, floor)
        out[key] = to_hex(new)
        changes.append((key, variables.get(key), out[key]))

    return out, changes
