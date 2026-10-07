#!/usr/bin/env python3
"""Pick a readable foreground for a background by measurement, not by name.

The audit scores pairs as a preset writes them. The UI composes pairs that
appear nowhere in the preset — white on the accent, the destructive colour as
text on a card — and those are where the failures were (see the 2026-07-30
entry in Concepts.md). This answers the question the lookup table could not:
given *this* background, which colour should the text be?

The rule:
  1. Gather candidates: every palette shade plus the preset's named
     foregrounds (window_fg, view_fg, ...).
  2. Keep the ones that clear a contrast floor against the background.
  3. Choose among them — by MODE:
       nearest-hue       smallest hue distance to the background, so the text
                         stays in the scheme's family (Rot gets pale sage on
                         its green accent, not white)
       highest-contrast  the most contrast available, which in practice means
                         the scheme's own near-white or near-black
  4. If nothing clears the floor, take the nearest-hue candidate and push its
     lightness away from the background until it does. The direction is
     decided by *measured* contrast in both directions, never by a luminance
     threshold — the white/black crossover sits at 0.179, not 0.5, and
     guessing pushed Conquest's mid-dark accent to white at 3.24:1.

Coloured text is the second shape: `destructive_color` drawn as a label on a
card. There the hue is the meaning (red means danger), so nothing is picked;
the colour keeps its hue and has its lightness pushed until it clears the
floor on every surface it is drawn on.

Usage:
  tools/pick-foreground.py                       # summary, all presets
  tools/pick-foreground.py --floor 5.0 --mode highest-contrast
  tools/pick-foreground.py --json out.json       # every variant, for review
"""
import argparse
import glob
import importlib.util
import json
import math
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "audit_contrast", os.path.join(_here, "audit-contrast.py"))
_audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_audit)
resolve, contrast = _audit.resolve, _audit.contrast

FLOORS = (4.5, 5.0)
MODES = ("nearest-hue", "highest-contrast")

# Fills: a foreground drawn on a coloured surface.
FILLS = ("accent", "destructive", "success", "warning", "error")
# Coloured text: the role colour drawn as a label on the neutral surfaces.
TEXT_SURFACES = ("window_bg_color", "view_bg_color", "card_bg_color")

NAMED_FG = ("window_fg_color", "view_fg_color", "card_fg_color",
            "headerbar_fg_color", "popover_fg_color", "dialog_fg_color",
            "sidebar_fg_color", "accent_fg_color")

# Hue distances inside one band count as equal, and contrast breaks the tie:
# two greens 1 and 4 degrees off a green accent are both "in family", and the
# more readable one should win.
HUE_BAND = 15.0
# Below this OKLCH chroma a colour has no meaningful hue.
ACHROMATIC = 0.02
# Hue distance charged when exactly one side is achromatic: worse than a
# near neighbour, better than the opposite side of the wheel.
NEUTRAL_HUE_PENALTY = 60.0


# --- OKLab / OKLCH -----------------------------------------------------------

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


def hexs(rgb):
    return "#%02x%02x%02x" % tuple(round(c) for c in rgb)


# --- picking -----------------------------------------------------------------

def candidates(preset):
    """Every colour the scheme offers as text: (label, rgb)."""
    v, out, seen = preset.get("variables", {}), [], set()
    base = resolve(v.get("window_bg_color"), v)
    for key in NAMED_FG:
        rgb = resolve(v.get(key), v, over=base)
        if rgb is not None:
            out.append((key.replace("_color", ""), rgb))
    for family, shades in sorted(preset.get("palette", {}).items()):
        for idx, value in sorted(shades.items()):
            rgb = resolve(value, v)
            if rgb is not None:
                out.append((f"{family}{idx}", rgb))
    unique = []
    for label, rgb in out:
        key = hexs(rgb)
        if key not in seen:
            seen.add(key)
            unique.append((label, tuple(round(c) for c in rgb)))
    return unique


def push(rgb, surfaces, floor):
    """Move `rgb` along OKLCH lightness until it clears `floor` on every
    surface. Both directions are measured; the one that gets there with the
    smaller move wins. Returns (rgb, reached)."""
    L, C, h = to_oklch(rgb)

    def worst(colour):
        return min(contrast(colour, s) for s in surfaces)

    best = None
    for target in (1.0, 0.0):
        lo, hi = L, target
        end = from_oklch(hi, C, h)
        if worst(end) < floor:
            continue                      # this direction never gets there
        for _ in range(30):
            mid = (lo + hi) / 2
            if worst(from_oklch(mid, C, h)) >= floor:
                hi = mid
            else:
                lo = mid
        found = from_oklch(hi, C, h)
        move = abs(hi - L)
        if best is None or move < best[0]:
            best = (move, found)
    if best is None:
        # Neither direction clears it: give the most contrast there is.
        ends = [from_oklch(1.0, C, h), from_oklch(0.0, C, h)]
        return max(ends, key=worst), False
    return best[1], True


def pick(bg, cands, floor, mode):
    """Foreground for a fill. Returns a dict describing the choice."""
    scored = [(label, rgb, contrast(rgb, bg), hue_distance(rgb, bg))
              for label, rgb in cands]
    clear = [s for s in scored if s[2] >= floor]
    if clear:
        if mode == "nearest-hue":
            label, rgb, ratio, dh = min(
                clear, key=lambda s: (s[3] // HUE_BAND, -s[2]))
        else:
            label, rgb, ratio, dh = max(clear, key=lambda s: s[2])
        return {"hex": hexs(rgb), "ratio": round(ratio, 2), "source": label,
                "how": "picked", "hue_distance": round(dh)}
    # Nothing in the palette is readable here: push the closest-in-family one.
    if mode == "nearest-hue":
        label, rgb, _, _ = min(scored, key=lambda s: (s[3], -s[2]))
    else:
        label, rgb, _, _ = max(scored, key=lambda s: s[2])
    out, reached = push(rgb, [bg], floor)
    return {"hex": hexs(out), "ratio": round(contrast(out, bg), 2),
            "source": label, "how": "pushed" if reached else "best-effort",
            "hue_distance": round(hue_distance(out, bg))}


def analyse(path):
    preset = json.load(open(path))
    v = preset.get("variables", {})
    base = resolve(v.get("window_bg_color"), v)
    cands = candidates(preset)
    result = {"name": preset.get("name", os.path.basename(path)),
              "file": os.path.basename(path), "fills": {}, "text": {}}
    surfaces = {k: resolve(v.get(k), v, over=base) for k in TEXT_SURFACES}
    surfaces = {k: s for k, s in surfaces.items() if s is not None}
    result["surfaces"] = {k: hexs(s) for k, s in surfaces.items()}
    for role in FILLS:
        bg = resolve(v.get(f"{role}_bg_color"), v, over=base)
        if bg is None:
            continue
        cur = resolve(v.get(f"{role}_fg_color"), v, over=bg)
        entry = {"bg": hexs(bg),
                 "current": None if cur is None else
                 {"hex": hexs(cur), "ratio": round(contrast(cur, bg), 2)},
                 "variants": {}}
        for floor in FLOORS:
            for mode in MODES:
                entry["variants"][f"{floor}/{mode}"] = pick(bg, cands,
                                                            floor, mode)
        result["fills"][role] = entry
    for role in FILLS:
        col = resolve(v.get(f"{role}_color"), v, over=base)
        if col is None or not surfaces:
            continue
        worst_now = min(contrast(col, s) for s in surfaces.values())
        entry = {"current": {"hex": hexs(col), "ratio": round(worst_now, 2)},
                 "variants": {}}
        for floor in FLOORS:
            if worst_now >= floor:
                out, ratio = col, worst_now
            else:
                out, _ = push(col, list(surfaces.values()), floor)
                ratio = min(contrast(out, s) for s in surfaces.values())
            entry["variants"][str(floor)] = {"hex": hexs(out),
                                             "ratio": round(ratio, 2)}
        result["text"][role] = entry
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("presets", nargs="*")
    ap.add_argument("--floor", type=float, default=4.5)
    ap.add_argument("--mode", choices=MODES, default="nearest-hue")
    ap.add_argument("--json", metavar="PATH",
                    help="write every variant for every preset to PATH")
    args = ap.parse_args()
    paths = args.presets or sorted(glob.glob("data/presets/*.json"))
    results = [analyse(p) for p in paths]

    if args.json:
        with open(args.json, "w") as f:
            json.dump(results, f, indent=1)

    key = f"{args.floor}/{args.mode}"
    picked = pushed = effort = failing_now = 0
    worst = (99, "")
    for r in results:
        for role, e in r["fills"].items():
            c = e["variants"].get(key)
            if c is None:
                continue
            picked += c["how"] == "picked"
            pushed += c["how"] == "pushed"
            effort += c["how"] == "best-effort"
            cur = e["current"]
            failing_now += cur is None or cur["ratio"] < args.floor
            worst = min(worst, (c["ratio"], f"{r['name']} {role}"))
    print(f"{len(results)} presets, floor {args.floor}, {args.mode}")
    print(f"  fills picked from the palette: {picked}")
    print(f"  fills pushed:                  {pushed}")
    print(f"  fills that cannot reach it:    {effort}"
          "  (no text colour clears the floor on that fill)")
    print(f"  fills below the floor today:   {failing_now}")
    print(f"  worst fill: {worst[0]:.2f}  ({worst[1]})")
    failing_text = sum(1 for r in results for e in r["text"].values()
                       if e["current"]["ratio"] < args.floor)
    print(f"  coloured-text roles below the floor today: {failing_text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
