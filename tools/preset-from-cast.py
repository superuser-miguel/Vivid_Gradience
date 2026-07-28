#!/usr/bin/env python3
"""Build a preset from an extracted colour cast.

A cast (see palette-from-image.py) is 90 colours with no meaning attached.
A preset needs semantic roles. This assigns them.

Two things shape the approach:

  * Roles, not variables. Monet already maps a handful of semantic roles onto
    all 46 named colours (see gradience/backend/theming/monet.py). The same
    idea applies here: pick surfaces, foreground, accent and status colours,
    and the rest follows.

  * Choose, don't modify. The Pastel/Neon presets were generated, so colours
    could be nudged darker until they cleared WCAG AA. A cast is somebody's
    artwork, so nudging it defeats the point — but with 90 candidates the
    contrast requirement can almost always be met by *picking* a different
    swatch instead. Only label colours fall back to a treatment rather than a
    colour (warning keeps Adwaita's black-at-80%).

Each cast row is already a 5-step ramp, light to dark, which lines up with
both a palette ramp (shades 1-5) and libadwaita's surface elevation ladder.

Usage:
  tools/preset-from-cast.py cast.json --name "Eminence" --out data/presets/
  tools/preset-from-cast.py cast.json --name "Fear" --mode light
"""
import argparse
import colorsys
import json
import os
import sys

AA = 4.5
BLACK_80 = "rgba(0, 0, 0, 0.8)"

# Canonical hues for the named palette ramps and the status colours.
RAMP_HUES = {"red_": 0, "orange_": 28, "yellow_": 50, "green_": 125,
             "blue_": 215, "purple_": 285, "brown_": 25}
STATUS_HUES = {"error": 0, "destructive": 0, "warning": 45, "success": 130}
STATUS_CANON = {"error": "#e01b24", "destructive": "#e01b24",
                "warning": "#f5c211", "success": "#2ec27e"}


def hx(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def to(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in c)


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = hx(c) if isinstance(c, str) else c
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def hls(c):
    r, g, b = (v / 255 for v in hx(c))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, l, s


def hue_dist(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def blend(a, b, t):
    return to(tuple(x + (y - x) * t for x, y in zip(hx(a), hx(b))))


def composite_black80(bg):
    return to(tuple(v * 0.2 for v in hx(bg)))


def best_fg(bg, dark_tone, light_tone):
    """Most readable label colour available for this background."""
    cands = [("#ffffff", contrast("#ffffff", bg)),
             (light_tone, contrast(light_tone, bg)),
             (BLACK_80, contrast(composite_black80(bg), bg)),
             (dark_tone, contrast(dark_tone, bg))]
    return max(cands, key=lambda c: c[1])[0]


def load_cast(path):
    rows = json.load(open(path))
    # Each row light -> dark, so it doubles as a palette ramp and an
    # elevation ladder.
    return [sorted(r, key=lum, reverse=True) for r in rows]


def row_stats(row):
    hs = [hls(c) for c in row]
    # circular mean of hue, weighted by saturation so greys don't drag it
    import math
    x = sum(math.cos(math.radians(h)) * s for h, _, s in hs)
    y = sum(math.sin(math.radians(h)) * s for h, _, s in hs)
    hue = math.degrees(math.atan2(y, x)) % 360
    return {
        "hue": hue,
        "lum": sum(lum(c) for c in row) / len(row),
        "sat": sum(s for _, _, s in hs) / len(hs),
        "chroma": max(s for _, _, s in hs),
    }


def pick_surfaces(rows, stats, fg, dark, margin=4.7):
    """Choose the surface family by what the text can actually sit on.

    Positional picking ("take shade 4 for the card") fails because a cast row
    spans its whole hue family, so the far end of a light row is a mid-tone
    that dark text cannot meet AA against. Instead, keep only the shades that
    genuinely clear contrast against the foreground, and prefer the row
    offering the widest usable ladder. Calm rows win ties so accents stand out.

    Returns (view, window, headerbar, card, sidebar) or None.
    """
    # Surfaces carry the whole window, so they must stay calm — the accent is
    # what brings colour. A saturated row that merely happens to offer more
    # readable shades must not win: that is how a cast ends up with a bright
    # pink window. Prefer quiet rows outright, and only consider loud ones if
    # the cast has nothing else.
    def candidates(lo, hi):
        out = []
        for i, row in enumerate(rows):
            if not lo <= stats[i]["sat"] <= hi:
                continue
            usable = [c for c in row if contrast(fg, c) >= margin]
            if len(usable) < 2:
                continue
            spread = abs(lum(usable[0]) - lum(usable[-1]))
            out.append(((len(usable), spread), usable))
        return out

    # Aim for a saturation band, not a minimum. Minimising it strips the cast's
    # character — Hatred collapsed to a neutral near-black instead of its warm
    # oxblood — while ignoring it lets a loud row take the window. Tinted but
    # quiet is the target; fall outward only if the cast offers nothing there.
    pool = (candidates(0.08, 0.38) or candidates(0.0, 0.38)
            or candidates(0.0, 0.55) or candidates(0.0, 1.0))
    if not pool:
        return None
    best = max(pool, key=lambda e: e[0])

    u = best[1]                      # light -> dark, all readable
    def at(idx):
        return u[max(0, min(len(u) - 1, idx))]

    if dark:
        # view darkest, window above it, card and headerbar lifted off it
        return at(len(u) - 1), at(len(u) - 2), at(len(u) - 3), at(len(u) - 3), at(len(u) - 3)
    # light: view and card brightest, window below, headerbar/sidebar dimmer
    return at(0), at(1), at(2), at(0), at(2)


def pick_accent(rows, stats, bg, card, dark_tone, light_tone):
    """Most colourful swatch that can carry a label and still stand out.

    Separating from the window is not enough — an accent that blends into the
    card reads as another surface rather than a button, which is what made
    Agony's first pass look flat.
    """
    cands = []
    for row in rows:
        for c in row:
            _, _, s = hls(c)
            if contrast(c, bg) < 1.8 or contrast(c, card) < 1.8:
                continue
            fg = best_fg(c, dark_tone, light_tone)
            fgc = composite_black80(c) if fg == BLACK_80 else fg
            if contrast(fgc, c) < AA:
                continue
            cands.append((s, c, fg))
    if not cands:
        return None, None

    # Chroma is the usual signal, but some casts have none — Rot and Agony are
    # muted throughout, and picking their "most saturated" swatch still yields
    # something indistinguishable from the surfaces. When that happens, fall
    # back to lightness contrast so the button at least reads as a button.
    # Fear arrives at its pale blue accent this way.
    if max(e[0] for e in cands) < 0.25:
        s, c, fg = max(cands, key=lambda e: (round(contrast(e[1], card), 1), e[0]))
    else:
        s, c, fg = max(cands, key=lambda e: e[0])
    return c, fg


def pick_status(rows, target_hue, canon, dark_tone, light_tone):
    """Nearest swatch by hue; blended toward the canonical colour if the cast
    has nothing in that part of the wheel, so an error still reads as one."""
    best, best_d = None, 1e9
    for row in rows:
        for c in row:
            h, l, s = hls(c)
            if s < 0.12 or l < 0.12 or l > 0.9:
                continue
            d = hue_dist(h, target_hue)
            if d < best_d:
                best, best_d = c, d
    if best is None:
        best, best_d = canon, 0
    if best_d > 45:
        best = blend(best, canon, min(0.6, (best_d - 45) / 120 + 0.3))
    # Selection first; only if nothing in the cast can carry a label do we
    # lean on the canonical colour.
    fg = best_fg(best, dark_tone, light_tone)
    fgc = composite_black80(best) if fg == BLACK_80 else fg
    if contrast(fgc, best) < AA:
        best = blend(best, canon, 0.5)
    return best


def assign_ramps(rows, stats):
    """One cast row per named ramp, greedily by hue, then lightness extremes."""
    used = set()
    out = {}
    order = sorted(RAMP_HUES.items(), key=lambda kv: -max(
        s["chroma"] for s in stats))
    for name, target in order:
        best, best_d = None, 1e9
        for i, st in enumerate(stats):
            if i in used or st["chroma"] < 0.08:
                continue
            d = hue_dist(st["hue"], target)
            if d < best_d:
                best, best_d = i, d
        if best is None:                       # cast has no chromatic rows left
            best = min((i for i in range(len(rows)) if i not in used),
                       key=lambda i: abs(stats[i]["lum"] - 0.4), default=0)
        used.add(best)
        out[name] = rows[best]
    light = max(range(len(rows)), key=lambda i: stats[i]["lum"])
    dark = min(range(len(rows)), key=lambda i: stats[i]["lum"])
    out["light_"] = rows[light]
    out["dark_"] = rows[dark]
    return out


def build(cast_path, name, mode):
    rows = load_cast(cast_path)
    flat = [c for r in rows for c in r]
    stats = [row_stats(r) for r in rows]

    if mode == "auto":
        med = sorted(lum(c) for c in flat)[len(flat) // 2]
        dark = med < 0.18
    else:
        dark = mode == "dark"

    light_tone = max(flat, key=lum)
    dark_tone = min(flat, key=lum)

    # Foreground first, since it decides which surfaces are usable at all.
    # Taken from the cast: the lightest swatch for a dark theme, darkest for
    # a light one.
    fg = light_tone if dark else dark_tone
    surfaces = pick_surfaces(rows, stats, fg, dark)
    if surfaces is None:
        # Nothing in the cast can carry its own extreme; fall back to plain
        # white/black text rather than shipping an unreadable preset.
        fg = "#ffffff" if dark else "#000000"
        surfaces = pick_surfaces(rows, stats, fg, dark)
    if surfaces is None:
        sys.exit(f"{name}: no surface family in this cast can meet AA")
    view, window, header, card, sidebar = surfaces

    accent, accent_fg = pick_accent(rows, stats, window, card, dark_tone, light_tone)
    if accent is None:
        accent = max(flat, key=lambda c: hls(c)[2])
        accent_fg = best_fg(accent, dark_tone, light_tone)

    status = {k: pick_status(rows, STATUS_HUES[k], STATUS_CANON[k],
                             dark_tone, light_tone)
              for k in ("error", "destructive", "success", "warning")}

    shade = "rgba(0, 0, 0, 0.36)" if dark else "rgba(0, 0, 0, 0.07)"
    v = {
        "accent_color": accent, "accent_bg_color": accent,
        "accent_fg_color": accent_fg,
        "destructive_color": status["destructive"],
        "destructive_bg_color": status["destructive"],
        "destructive_fg_color": best_fg(status["destructive"], dark_tone, light_tone),
        "success_color": status["success"], "success_bg_color": status["success"],
        "success_fg_color": best_fg(status["success"], dark_tone, light_tone),
        "warning_color": status["warning"], "warning_bg_color": status["warning"],
        # Adwaita's black-at-80% label where the warning colour is light
        # enough to take it; otherwise whatever actually reads.
        "warning_fg_color": (
            BLACK_80
            if contrast(composite_black80(status["warning"]), status["warning"]) >= AA
            else best_fg(status["warning"], dark_tone, light_tone)),
        "error_color": status["error"], "error_bg_color": status["error"],
        "error_fg_color": best_fg(status["error"], dark_tone, light_tone),
        "window_bg_color": window, "window_fg_color": fg,
        "view_bg_color": view, "view_fg_color": fg,
        "headerbar_bg_color": header, "headerbar_fg_color": fg,
        "headerbar_border_color": fg,
        "headerbar_backdrop_color": "@window_bg_color",
        "headerbar_shade_color": shade,
        "headerbar_darker_shade_color": (
            "rgba(0, 0, 0, 0.9)" if dark else "rgba(0, 0, 0, 0.12)"),
        "card_bg_color": card, "card_fg_color": fg, "card_shade_color": shade,
        "dialog_bg_color": card, "dialog_fg_color": fg,
        "popover_bg_color": card, "popover_fg_color": fg,
        "popover_shade_color": shade, "shade_color": shade,
        "scrollbar_outline_color": (
            "rgba(0, 0, 0, 0.5)" if dark else "#ffffff"),
        "thumbnail_bg_color": card, "thumbnail_fg_color": fg,
        "sidebar_bg_color": sidebar, "sidebar_fg_color": fg,
        "sidebar_border_color": view, "sidebar_backdrop_color": window,
        "sidebar_shade_color": shade,
        "secondary_sidebar_bg_color": view, "secondary_sidebar_fg_color": fg,
        "secondary_sidebar_backdrop_color": view,
        "secondary_sidebar_shade_color": shade,
    }

    ramps = assign_ramps(rows, stats)
    order = ["blue_", "green_", "yellow_", "orange_", "red_", "purple_",
             "brown_", "light_", "dark_"]
    palette = {h: {str(i + 1): ramps[h][i] for i in range(5)} for h in order}
    return {"name": name, "author": "Vivid Gradience",
            "license": "GPL-3.0-or-later", "variables": v,
            "palette": palette}, dark


PAIRS = [("window_fg_color", "window_bg_color"),
         ("view_fg_color", "view_bg_color"),
         ("headerbar_fg_color", "headerbar_bg_color"),
         ("card_fg_color", "card_bg_color"),
         ("dialog_fg_color", "dialog_bg_color"),
         ("popover_fg_color", "popover_bg_color"),
         ("thumbnail_fg_color", "thumbnail_bg_color"),
         ("sidebar_fg_color", "sidebar_bg_color"),
         ("secondary_sidebar_fg_color", "secondary_sidebar_bg_color"),
         ("accent_fg_color", "accent_bg_color"),
         ("destructive_fg_color", "destructive_bg_color"),
         ("success_fg_color", "success_bg_color"),
         ("warning_fg_color", "warning_bg_color"),
         ("error_fg_color", "error_bg_color")]


def audit(v):
    worst, fails = (99, ""), []
    for fgk, bgk in PAIRS:
        a, b = v[fgk], v[bgk]
        if not b.startswith("#"):
            continue
        a = composite_black80(b) if a == BLACK_80 else a
        if not a.startswith("#"):
            continue
        c = contrast(a, b)
        if c < worst[0]:
            worst = (c, fgk.replace("_color", ""))
        if c < AA:
            fails.append((fgk, bgk, c))
    return worst, fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cast")
    ap.add_argument("--name", required=True)
    ap.add_argument("--mode", choices=("auto", "dark", "light"), default="auto")
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    preset, dark = build(args.cast, args.name, args.mode)
    worst, fails = audit(preset["variables"])
    slug = args.name.lower().replace(" ", "-")
    path = os.path.join(args.out, slug + ".json")
    with open(path, "w") as f:
        json.dump(preset, f, indent=2)
        f.write("\n")
    kind = "dark" if dark else "light"
    print(f"{args.name:12s} {kind:5s} bg={preset['variables']['window_bg_color']} "
          f"accent={preset['variables']['accent_bg_color']} "
          f"worst={worst[1]} {worst[0]:.2f}" + ("  FAILS" if fails else ""))
    for fgk, bgk, c in fails:
        print(f"   FAIL {fgk} on {bgk}: {c:.2f}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
