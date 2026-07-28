#!/usr/bin/env python3
"""Score every bundled preset's foreground/background pairs against WCAG.

The presets this project generated were checked as they were built. The ones
inherited from upstream never have been, and some predate any contrast
thinking at all — so this exists to find out where the bundled set actually
stands.

Resolving a colour is the fiddly part. A variable may be a hex value, an
`@reference` to another variable, or an `rgba()` that only has a real colour
once composited over whatever sits behind it.

Usage:
  tools/audit-contrast.py                     # all presets, failures only
  tools/audit-contrast.py --all               # every preset, pass or fail
  tools/audit-contrast.py --level AAA         # 7.0 instead of 4.5
  tools/audit-contrast.py data/presets/nord.json
"""
import argparse
import glob
import json
import os
import re
import sys

AA, AAA = 4.5, 7.0

PAIRS = [
    ("window_fg_color", "window_bg_color"),
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
    ("error_fg_color", "error_bg_color"),
]

RGBA = re.compile(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)"
                  r"(?:\s*,\s*([\d.]+))?\s*\)")


def hx(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def resolve(value, variables, over=None, depth=0):
    """A colour as RGB, or None if it cannot be pinned down.

    `over` is what the colour sits on, needed to composite a translucent one.
    """
    if value is None or depth > 8:
        return None
    value = value.strip()
    if value.startswith("@"):
        return resolve(variables.get(value[1:]), variables, over, depth + 1)
    if value.startswith("#"):
        if len(value) == 7:
            return hx(value)
        if len(value) == 4:                       # #abc
            return tuple(int(ch * 2, 16) for ch in value[1:])
        return None
    m = RGBA.match(value)
    if m:
        r, g, b = (float(m.group(i)) for i in (1, 2, 3))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        if a >= 1.0:
            return (r, g, b)
        if over is None:
            return None
        return tuple(c * a + o * (1 - a) for c, o in zip((r, g, b), over))
    return None


def lum(rgb):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def audit(path, threshold):
    d = json.load(open(path))
    v = d.get("variables", {})
    results, unresolved = [], []
    # A translucent surface (Adwaita Dark's card is rgba(255,255,255,0.08))
    # only has a real colour once composited over what it sits on, which for
    # every surface here is the window.
    base = resolve(v.get("window_bg_color"), v)
    for fgk, bgk in PAIRS:
        if fgk not in v or bgk not in v:
            continue
        bg = resolve(v[bgk], v, over=base)
        if bg is None:
            unresolved.append(bgk)
            continue
        fg = resolve(v[fgk], v, over=bg)
        if fg is None:
            unresolved.append(fgk)
            continue
        results.append((contrast(fg, bg), fgk, bgk))
    return d.get("name", os.path.basename(path)), results, unresolved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("presets", nargs="*",
                    default=sorted(glob.glob("data/presets/*.json")))
    ap.add_argument("--all", action="store_true",
                    help="list every preset, not just the ones with failures")
    ap.add_argument("--level", choices=("AA", "AAA"), default="AA")
    args = ap.parse_args()

    threshold = AA if args.level == "AA" else AAA
    paths = args.presets or sorted(glob.glob("data/presets/*.json"))

    failing, checked, pairs_checked, worst_overall = [], 0, 0, (99, "", "")
    for path in paths:
        name, results, unresolved = audit(path, threshold)
        if not results:
            continue
        checked += 1
        pairs_checked += len(results)
        fails = [r for r in results if r[0] < threshold]
        worst = min(results)
        if worst < worst_overall:
            worst_overall = worst
        if fails:
            failing.append((name, os.path.basename(path), fails, worst))
        elif args.all:
            print(f"  ok   {name:22s} worst {worst[1].replace('_color',''):24s}"
                  f" {worst[0]:5.2f}")
        if unresolved:
            print(f"  ??   {name}: could not resolve {', '.join(unresolved)}")

    if failing:
        print(f"\n{len(failing)} preset(s) below {args.level} "
              f"({threshold}:1)\n")
        for name, fname, fails, worst in sorted(failing, key=lambda e: e[3]):
            print(f"  {name}  ({fname})")
            for c, fgk, bgk in sorted(fails):
                print(f"      {c:5.2f}  {fgk.replace('_color','')}"
                      f" on {bgk.replace('_color','')}")
    print(f"\n{checked} presets, {pairs_checked} pairs checked at {args.level}"
          f" ({threshold}:1)")
    print(f"{len(failing)} preset(s) with at least one failing pair")
    print(f"lowest pair anywhere: {worst_overall[0]:.2f} "
          f"({worst_overall[1].replace('_color','')} on "
          f"{worst_overall[2].replace('_color','')})")
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
