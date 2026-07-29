#!/usr/bin/env python3
"""Lean a preset's colour family toward a different hue.

Pastels live in a narrow slice of the colour space, so two of them can sit a
few degrees apart and read as the same theme. This rotates a preset's family
signature — surfaces, accent, foregrounds — onto a new hue, so it separates
from its neighbours without leaving the pastel range.

Not everything rotates by the same amount, because not every colour is free to
move:

  signature  surfaces, accent, foregrounds, borders   full rotation
  ramps      the nine named palette ramps             partial (--ramp-pull)
  status     destructive / success / warning / error  never — a warning that
                                                      rotates off amber stops
                                                      reading as a warning

Greys, `rgba()` shades and `@references` are left alone. Edits are textual, so
the file keeps its existing indentation.

    tools/shift-preset-hue.py data/presets/bluebell.json --to-hue 193 --dry-run
    tools/shift-preset-hue.py data/presets/bluebell.json --to-hue 193 --sat 1.15
"""
import argparse
import colorsys
import json
import re
import sys

SIGNATURE = "window_bg_color"
STATUS = ("destructive", "success", "warning", "error")


def to_hls(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)


def to_hex(hls):
    r, g, b = colorsys.hls_to_rgb(*hls)
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02x}" for c in (r, g, b))


def shift(hexcode, dh, sat=1.0, light=1.0):
    h, l, s = to_hls(hexcode)
    if s < 0.02:  # a grey has no hue to rotate
        return hexcode
    return to_hex((
        (h + dh / 360.0) % 1.0,
        max(0.0, min(1.0, l * light)),
        max(0.0, min(1.0, s * sat)),
    ))


def rewrite(text, mapping):
    """Replace whole JSON string values, longest first, without reformatting."""
    for before in sorted(mapping, key=len, reverse=True):
        text = text.replace(f'"{before}"', f'"{mapping[before]}"')
    return text


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("preset")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--hue", type=float, help="rotate by this many degrees")
    g.add_argument("--to-hue", type=float,
                   help=f"rotate so {SIGNATURE} lands on this hue")
    ap.add_argument("--sat", type=float, default=1.0,
                    help="saturation multiplier for the signature")
    ap.add_argument("--accent-light", type=float, default=1.0,
                    help="lightness multiplier for the accent only — a hue that "
                         "rotates toward yellow/cyan gets lighter, and may need "
                         "pulling back down to hold WCAG AA")
    ap.add_argument("--ramp-pull", type=float, default=0.35,
                    help="fraction of the rotation applied to the named palette "
                         "ramps (0 = leave them, 1 = move them with the family)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = open(a.preset).read()
    d = json.loads(src)
    variables, palette = d["variables"], d.get("palette", {})

    sig = variables.get(SIGNATURE, "")
    if not sig.startswith("#"):
        sys.exit(f"{a.preset}: {SIGNATURE} is not a hex colour ({sig!r})")
    sig_hue = to_hls(sig)[0] * 360
    dh = a.hue if a.hue is not None else a.to_hue - sig_hue

    print(f"{d.get('name', a.preset)}: {SIGNATURE} {sig} {sig_hue:.0f}deg "
          f"-> {(sig_hue + dh) % 360:.0f}deg   rotate {dh:+.0f}, sat x{a.sat}, "
          f"ramps x{a.ramp_pull}")

    mapping, held = {}, []
    for name, value in variables.items():
        if not isinstance(value, str) or not value.startswith("#"):
            continue
        if any(name.startswith(s) for s in STATUS):
            held.append(name)
            continue
        light = a.accent_light if name.startswith("accent") else 1.0
        mapping[value] = shift(value, dh, a.sat, light)
    for prefix, shades in palette.items():
        for value in shades.values():
            # A ramp already claimed by a variable keeps that variable's result;
            # otherwise it leans partway, so `red_` still reads red.
            mapping.setdefault(value, shift(value, dh * a.ramp_pull, a.sat))

    mapping = {k: v for k, v in mapping.items() if k != v}
    print(f"  {len(mapping)} distinct colours moved; "
          f"{len(held)} status colours held ({', '.join(sorted(set(h.split('_')[0] for h in held)))})")

    if a.dry_run:
        for name in ("accent_bg_color", SIGNATURE, "view_bg_color",
                     "headerbar_bg_color", "card_bg_color", "window_fg_color"):
            v = variables.get(name, "")
            if v in mapping:
                print(f"    {name:20} {v} -> {mapping[v]}")
        for prefix in list(palette)[:4]:
            row = " ".join(mapping.get(palette[prefix][str(i)], palette[prefix][str(i)])
                           for i in range(1, 6))
            print(f"    {prefix:20} {row}")
        return

    open(a.preset, "w").write(rewrite(src, mapping))
    print(f"  wrote {a.preset}")


if __name__ == "__main__":
    main()
