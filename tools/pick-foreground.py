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
  tools/pick-foreground.py --verify              # check what Apply writes
"""
import argparse
import glob
import importlib.util
import json
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
# The engine's own module, loaded by path: it has no GTK imports, so the tool
# measures exactly what an Apply would write.
_spec = importlib.util.spec_from_file_location(
    "contrast", os.path.join(_here, "..", "gradience", "backend", "utils",
                             "contrast.py"))
_c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_c)

FLOORS = (4.5, 5.0)
MODES = ("nearest-hue", "highest-contrast")
FILLS = _c.FILL_ROLES
TEXT_SURFACES = _c.TEXT_SURFACES
contrast, hexs, push = _c.contrast, _c.to_hex, _c.push


def _pick(bg, cands, floor, mode):
    rgb, how, source = _c.pick(bg, cands, floor, mode)
    return {"hex": hexs(rgb), "ratio": round(contrast(rgb, bg), 2),
            "source": source, "how": how,
            "hue_distance": round(_c.hue_distance(rgb, bg))}


def analyse(path):
    preset = json.load(open(path))
    v = preset.get("variables", {})
    names = dict(_c.flatten_palette(preset.get("palette")))
    names.update(v)

    def resolve(value, _vars, over=None):
        return _c.resolve(value, names, over)

    base = resolve(v.get("window_bg_color"), v)
    cands = _c.candidates(v, preset.get("palette"))
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
                entry["variants"][f"{floor}/{mode}"] = _pick(bg, cands,
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


def verify(paths, floor=_c.FLOOR):
    """Run the engine's readable_variables() over every preset and score the
    result: every text role and every fill must clear the floor, and every
    value that already did must come out untouched. Returns failures."""
    failures, changed, presets_changed = [], 0, 0
    for path in paths:
        preset = json.load(open(path))
        v, pal = preset.get("variables", {}), preset.get("palette")
        out, changes = _c.readable_variables(v, pal, floor)
        name = preset.get("name", os.path.basename(path))
        changed += len(changes)
        presets_changed += bool(changes)
        names = dict(_c.flatten_palette(pal))
        names.update(out)
        base = _c.resolve(out.get("window_bg_color"), names)
        surfaces = [s for s in (_c.resolve(out.get(k), names, over=base)
                                for k in TEXT_SURFACES) if s is not None]
        for role in FILLS:
            col = _c.resolve(out.get(f"{role}_color"), names, over=base)
            if col is not None and surfaces:
                r = min(contrast(col, s) for s in surfaces)
                if r < floor - 1e-9:
                    failures.append(f"{name}: {role}_color {r:.2f}")
            bg = _c.resolve(out.get(f"{role}_bg_color"), names, over=base)
            fg = _c.resolve(out.get(f"{role}_fg_color"), names, over=bg)
            if bg is not None and fg is not None and contrast(fg, bg) < floor - 1e-9:
                failures.append(f"{name}: {role}_fg on {role}_bg "
                                f"{contrast(fg, bg):.2f}")
        touched = {k for k, _, _ in changes}
        for k in v:
            if k not in touched and out[k] != v[k]:
                failures.append(f"{name}: {k} changed without being reported")
    print(f"{len(paths)} presets checked at {floor}:1")
    print(f"  values replaced: {changed}, in {presets_changed} presets")
    print(f"  failures: {len(failures)}")
    for f in failures:
        print(f"    {f}")
    return failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("presets", nargs="*")
    ap.add_argument("--floor", type=float, default=4.5)
    ap.add_argument("--mode", choices=MODES, default="nearest-hue")
    ap.add_argument("--json", metavar="PATH",
                    help="write every variant for every preset to PATH")
    ap.add_argument("--verify", action="store_true",
                    help="score what Apply would write, and fail on any "
                         "role below the floor")
    args = ap.parse_args()
    paths = args.presets or sorted(glob.glob("data/presets/*.json"))
    if args.verify:
        return 1 if verify(paths) else 0
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
