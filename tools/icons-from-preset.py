#!/usr/bin/env python3
"""Build a recoloured "pseudo-Adwaita" icon theme from a preset.

Adwaita's folder icons are blue because the blue is written into the SVGs. No
colour variable reaches them, so a themed desktop keeps stock-blue folders --
the seam you notice as soon as a file manager is open.

The set is small. Of Adwaita's 70 full-colour icons, roughly twenty are blue at
all -- folders, a few mimetypes, the network and display devices. The other
fifty are greys, and greys are meant to stay grey.

Those blues are not a five-value palette. They are 29 distinct colours spanning
luminance 0.05 to 0.98, all sitting within a few degrees of hue 213 -- a
continuous shading family covering folder flaps, gradient stops, monitor
glow and network globes. Substituting a fixed list positionally leaves whatever
is not on the list untouched, which is how you get a folder that themes and a
monitor beside it still glowing Adwaita blue.

So every blue is mapped through a luminance curve built from the chosen ramp,
which preserves the ordering that made the shading read as shading. The curve is
extended past the ramp's own range toward white and black, so highlights stay
highlights instead of compressing into a flat patch.

Which ramp is not a matter of taste. A folder has to stay visible against the
file manager's own background, so ramps are scored for contrast against
`view_bg_color` first, and only then for how close they sit to the preset's
accent. Choosing by name instead produces folders that vanish -- Hatred's red
ramp against Hatred's near-black view is the case that proved it.

Nothing is applied. The theme is written and the command to select it printed,
unless you pass --apply.

    tools/icons-from-preset.py data/presets/rot.json
    tools/icons-from-preset.py data/presets/rot.json --list-ramps
    tools/icons-from-preset.py data/presets/rot.json --ramp purple_ --apply
"""
import argparse
import colorsys
import json
import os
import re
import shutil
import subprocess
import sys

ADWAITA = "/usr/share/icons/Adwaita"
CONTEXTS = {"places": "Places", "devices": "Devices",
            "mimetypes": "MimeTypes", "status": "Status"}
# Below this, a folder stops reading as a folder against the view behind it.
MIN_VISIBLE = 1.9
# What counts as "Adwaita blue". Measured rather than guessed: every blue in the
# icon set falls between hue 206 and 220. The band is widened a little for
# headroom, and the saturation floor keeps neutral greys out -- a grey drawer
# front or device bezel is not part of the folder's colour.
BLUE_HUE = (195, 250)
BLUE_MIN_SAT = 0.25
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


def rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def lum(h):
    def f(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    x, y = sorted((lum(a), lum(b)))
    return (y + 0.05) / (x + 0.05)


def hue(h):
    return colorsys.rgb_to_hls(*rgb(h))[0] * 360


def hue_gap(a, b):
    d = abs(hue(a) - hue(b)) % 360
    return min(d, 360 - d)


def flatten(variables, name, over, depth=0):
    """Resolve @references and composite rgba() over a known background."""
    c = variables.get(name, over)
    if depth > 8:
        return over
    if isinstance(c, str) and c.startswith("@"):
        return flatten(variables, c[1:], over, depth + 1)
    m = re.match(r"rgba?\(([^)]*)\)", c or "")
    if m:
        p = [x.strip() for x in m.group(1).split(",")]
        if len(p) >= 3:
            fg = [float(x) / 255 for x in p[:3]]
            a = float(p[3]) if len(p) > 3 else 1.0
            bg = rgb(over)
            return "#" + "".join(
                f"{round(255 * (fg[i] * a + bg[i] * (1 - a))):02x}" for i in range(3))
    return c if isinstance(c, str) and c.startswith("#") else over


NEUTRAL_RAMPS = ("light_", "dark_")
# The folder's main body -- the most-used blue in the whole icon set (70 of the
# 222 blue occurrences). Ramps are scored by what THIS becomes, not by a shade
# picked out of the ramp: a cast-derived ramp can run cyan to purple within its
# own five shades, so its middle shade says very little about how the folder
# will actually look.
FOLDER_BODY = "#62a0ea"


def score_ramps(preset):
    """Rank the palette ramps by what the folder actually becomes under each."""
    variables, palette = preset["variables"], preset.get("palette", {})
    view = flatten(variables, "view_bg_color", "#ffffff")
    accent = flatten(variables, "accent_bg_color", "#3584e4")

    # A near-neutral accent has no hue to match against, so hue distance from it
    # is noise -- every ramp lands ~180deg away and the ordering is arbitrary.
    # Monochrome schemes are ranked purely on visibility.
    #
    # Measured as chroma rather than HLS saturation: saturation is scaled by
    # lightness, so it reads a dark-but-coloured accent as grey. Rot's #354437
    # is a green, and HLS calls it 0.12 saturated -- the same range as Agony's
    # genuinely neutral #c0c0bf. Chroma separates them cleanly, 0.059 to 0.004.
    r_, g_, b_ = rgb(accent)
    monochrome = (max(r_, g_, b_) - min(r_, g_, b_)) < 0.05

    rows = []
    for name, shades in palette.items():
        try:
            curve = make_curve([shades[str(i)] for i in range(1, 6)])
        except KeyError:
            continue
        body = remap(FOLDER_BODY, curve)
        rows.append({
            "ramp": name,
            "body": body,
            "contrast": contrast(body, view),
            "hue_gap": hue_gap(body, accent),
            "neutral": name in NEUTRAL_RAMPS,
        })

    def visible(rs):
        return [r for r in rs if r["contrast"] >= MIN_VISIBLE]

    # Coloured ramps are preferred while any of them is actually visible -- a
    # theme with colour in it should get a coloured folder. The grey ramps are
    # held back as a fallback, which is what rescues schemes whose every
    # chromatic ramp sits on top of the view.
    #
    # Except when the scheme is monochrome, where the grey ramp IS the themed
    # one. Holding it back there ranked Agony's light_ last despite it winning
    # on both contrast and hue.
    chromatic = [r for r in rows if not r["neutral"]]
    pool_is_chromatic = bool(visible(chromatic)) and not monochrome

    def key(r):
        return (
            r["neutral"] if pool_is_chromatic else False,
            r["contrast"] < MIN_VISIBLE,
            -r["contrast"] if (monochrome or not visible(rows)) else r["hue_gap"],
        )

    rows.sort(key=key)
    return rows, view, accent


def is_blue(h):
    hh, _, s = colorsys.rgb_to_hls(*rgb(h))
    return BLUE_HUE[0] <= hh * 360 <= BLUE_HUE[1] and s >= BLUE_MIN_SAT


def affected_icons():
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
            blues = {h.lower() for h in HEX.findall(data) if is_blue(h)}
            if blues:
                found.append((os.path.relpath(p, root), data, blues))
    return sorted(found)


def make_curve(shades):
    """A luminance -> colour curve from a ramp, extended past both ends.

    Adwaita's blues run nearly the full luminance range; a five-shade ramp does
    not. Without the extensions every highlight and every shadow would clamp to
    the ramp's own extremes and the icon would flatten out.
    """
    pts = sorted(((lum(s), s) for s in shades), key=lambda t: t[0])
    lightest, darkest = pts[-1][1], pts[0][1]

    def mix(a, b, t):
        x, y = rgb(a), rgb(b)
        return "#" + "".join(
            f"{round(255 * (x[i] + (y[i] - x[i]) * t)):02x}" for i in range(3))

    # Keep the family's hue at the extremes rather than fading to pure grey.
    top, bottom = mix(lightest, "#ffffff", 0.75), mix(darkest, "#000000", 0.6)
    return [(0.0, bottom)] + pts + [(1.0, top)]


def remap(h, curve):
    L = lum(h)
    for i in range(len(curve) - 1):
        (l0, c0), (l1, c1) = curve[i], curve[i + 1]
        if l0 <= L <= l1:
            t = 0.0 if l1 == l0 else (L - l0) / (l1 - l0)
            a, b = rgb(c0), rgb(c1)
            return "#" + "".join(
                f"{round(255 * (a[j] + (b[j] - a[j]) * t)):02x}" for j in range(3))
    return curve[-1][1] if L > curve[-1][0] else curve[0][1]


def build(preset, ramp_name, out_dir, theme_name):
    shades = [preset["palette"][ramp_name][str(i)] for i in range(1, 6)]
    curve = make_curve(shades)

    icons = affected_icons()
    if not icons:
        sys.exit(f"no recolourable icons found under {ADWAITA}/scalable")

    mapping = {}
    for _, _, blues in icons:
        for b in blues:
            mapping.setdefault(b, remap(b, curve))

    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)

    contexts = {}
    for rel, data, _ in icons:
        sub = os.path.dirname(rel)
        contexts.setdefault(sub, CONTEXTS.get(os.path.basename(sub), "Places"))
        dest = os.path.join(out_dir, "scalable", rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        out = HEX.sub(lambda m: mapping.get(m.group(0).lower(), m.group(0)), data)
        open(dest, "w", encoding="utf-8").write(out)

    dirs = sorted(contexts)
    index = [
        "[Icon Theme]",
        f"Name={theme_name}",
        f"Comment=Adwaita recoloured to match the {preset.get('name', 'preset')} scheme",
        # Inheriting is what keeps this a twenty-file theme instead of a fork:
        # anything not recoloured falls through to Adwaita itself.
        "Inherits=Adwaita",
        "Directories=" + ",".join(f"scalable/{d}" for d in dirs),
        "",
    ]
    for d in dirs:
        index += [f"[scalable/{d}]", "Size=128", "MinSize=8", "MaxSize=512",
                  f"Context={contexts[d]}", "Type=Scalable", ""]
    open(os.path.join(out_dir, "index.theme"), "w").write("\n".join(index))

    open(os.path.join(out_dir, "COPYING-Adwaita"), "w").write(
        "The icons in this theme are derived from the Adwaita icon theme,\n"
        "recoloured but otherwise unmodified.\n\n"
        "Adwaita icon theme, Copyright the GNOME Project.\n"
        "Licensed LGPL-3.0-only OR CC-BY-SA-3.0.\n"
        "https://gitlab.gnome.org/GNOME/adwaita-icon-theme\n\n"
        "This derived theme is distributed under the same terms.\n")

    return mapping, [rel for rel, _, _ in icons]


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("preset")
    ap.add_argument("--ramp", help="force a palette ramp, e.g. purple_")
    ap.add_argument("--name", default="VividGradience", help="theme directory name")
    ap.add_argument("--list-ramps", action="store_true",
                    help="show how every ramp scores and exit")
    ap.add_argument("--apply", action="store_true",
                    help="also set icon-theme (otherwise the command is printed)")
    a = ap.parse_args()

    if not os.path.isdir(ADWAITA):
        sys.exit(f"{ADWAITA} not found -- is adwaita-icon-theme installed?")

    preset = json.load(open(a.preset))
    rows, view, accent = score_ramps(preset)
    if not rows:
        sys.exit(f"{a.preset}: no usable palette ramps")

    print(f"{preset.get('name', a.preset)}   view {view}   accent {accent}")

    if a.list_ramps:
        print(f"\n  {'ramp':10} {'folder':9} {'contrast':>9}  {'hue gap':>8}")
        for r in rows:
            mark = "" if r["contrast"] >= MIN_VISIBLE else "   too faint"
            print(f"  {r['ramp']:10} {r['body']:9} {r['contrast']:9.2f}"
                  f"  {r['hue_gap']:7.0f}deg{mark}")
        return

    ramp = a.ramp or rows[0]["ramp"]
    if ramp not in preset.get("palette", {}):
        sys.exit(f"no ramp {ramp!r} in this preset "
                 f"(have: {', '.join(sorted(preset['palette']))})")
    chosen = next(r for r in rows if r["ramp"] == ramp)
    why = "forced" if a.ramp else (
        f"nearest accent among the visible ramps"
        if chosen["contrast"] >= MIN_VISIBLE else "most visible ramp available")
    print(f"ramp {ramp} -- {why} "
          f"(contrast {chosen['contrast']:.2f} vs view, "
          f"hue {chosen['hue_gap']:.0f}deg off accent)")

    out_dir = os.path.expanduser(f"~/.local/share/icons/{a.name}")
    mapping, files = build(preset, ramp, out_dir, a.name)

    print(f"\n  {len(files)} icons recoloured, {len(mapping)} blues remapped "
          f"-> {out_dir}")
    for s, d in sorted(mapping.items(), key=lambda kv: -lum(kv[0])):
        print(f"    {s} -> {d}   (lum {lum(s):.2f})")

    if a.apply:
        subprocess.run(["gsettings", "set", "org.gnome.desktop.interface",
                        "icon-theme", a.name], check=True)
        print(f"\n  icon-theme set to {a.name}")
    else:
        print(f"\nNot applied. To use it:\n"
              f"  gsettings set org.gnome.desktop.interface icon-theme '{a.name}'\n"
              f"To go back:\n"
              f"  gsettings reset org.gnome.desktop.interface icon-theme")


if __name__ == "__main__":
    main()
