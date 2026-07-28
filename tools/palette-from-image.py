#!/usr/bin/env python3
"""Pull a palette out of an image.

Two modes:

  grid       For screenshots of a swatch grid — an in-game colour picker, a
             palette site, a contact sheet. Finds the separator lines, then
             takes the median of each cell's interior so gridline bleed and
             anti-aliasing cannot skew the result. Exact colours, not guesses.

  dominant   For any other image. Median-cut quantisation down to N colours,
             reported most-common first.

Grid mode is the accurate one: it reports the colours that are actually in
the image. Dominant mode approximates, and how well it does depends entirely
on the picture.

Usage:
  tools/palette-from-image.py shot.png                 # auto-detect
  tools/palette-from-image.py shot.png --mode grid
  tools/palette-from-image.py shot.png --mode dominant --colors 12
  tools/palette-from-image.py shot.png --json out.json
"""
import argparse
import json
import statistics
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("needs Pillow:  pip install --user Pillow")


def luminance(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def to_hex(c):
    return "#%02x%02x%02x" % tuple(int(round(v)) for v in c)


def _local_dark_runs(profile, window=15, ratio=0.8, min_drop=6):
    """Stretches that are dark *relative to their surroundings*.

    An absolute brightness cut cannot find gridlines: a near-black palette has
    swatches darker than its own separators (HATRED's cells sit at luminance
    ~50 while its gridlines sit at ~28, but a bright palette's cells are at
    ~170). What is invariant is that a separator is markedly darker than the
    pixels either side of it, so the test is against a local baseline.
    """
    n = len(profile)
    runs = []
    for i, v in enumerate(profile):
        lo = max(0, i - window)
        hi = min(n, i + window + 1)
        baseline = statistics.median(profile[lo:hi])
        if v < baseline * ratio and v < baseline - min_drop:
            if runs and i == runs[-1][-1] + 1:
                runs[-1].append(i)
            else:
                runs.append([i])
    return [(r[0], r[-1]) for r in runs]


def _axis_bands(profile, total, max_sep=6, min_cell=8):
    """Content bands along one axis.

    Narrow dark runs are gridlines; wide ones are the outer frame and bound
    the content region. Splitting on width rather than depth is what makes
    this work on dark and light palettes alike.
    """
    runs = _local_dark_runs(profile)
    narrow = [(a, b) for a, b in runs if (b - a + 1) <= max_sep]
    wide = [(a, b) for a, b in runs if (b - a + 1) > max_sep]

    # The frame: widest dark run in each outer third bounds the content.
    start, end = 0, total - 1
    for a, b in wide:
        if b < total * 0.33 and b >= start:
            start = b + 1
        if a > total * 0.66 and a <= end:
            end = a - 1

    seps = [(a, b) for a, b in narrow if a > start and b < end]

    bands, prev = [], start
    for a, b in seps:
        if a - prev >= min_cell:
            bands.append((prev, a - 1))
        prev = b + 1
    if end - prev + 1 >= min_cell:
        bands.append((prev, end))

    if len(bands) >= 3:
        pitch = statistics.median(b - a + 1 for a, b in bands)
        # Drop stragglers: leftover margin slivers that are not a whole cell.
        bands = [(a, b) for a, b in bands if (b - a + 1) >= pitch * 0.6]
        # Split merged cells. Where two very dark swatches sit side by side the
        # gridline between them is no darker than they are, so no separator is
        # visible at all. The cells are on a regular pitch though, so a band
        # measuring a clean multiple of it is that many cells run together.
        split = []
        for a, b in bands:
            k = int(round((b - a + 1) / pitch))
            if k >= 2 and abs((b - a + 1) - k * pitch) <= pitch * 0.35:
                step = (b - a + 1) / k
                for i in range(k):
                    split.append((a + int(i * step), a + int((i + 1) * step) - 1))
            else:
                split.append((a, b))
        bands = split
    return bands


def detect_grid(im, min_cell=8):
    px = im.load()
    w, h = im.size
    med = statistics.median
    col_profile = [med(luminance(px[x, y]) for y in range(0, h, max(1, h // 100)))
                   for x in range(w)]
    row_profile = [med(luminance(px[x, y]) for x in range(0, w, max(1, w // 100)))
                   for y in range(h)]
    xs = _axis_bands(col_profile, w, min_cell=min_cell)
    ys = _axis_bands(row_profile, h, min_cell=min_cell)
    return xs, ys


def sample_cell(px, x0, x1, y0, y1):
    """Median of the cell's middle half — ignores edges entirely."""
    mx = max(1, (x1 - x0) // 4)
    my = max(1, (y1 - y0) // 4)
    pixels = [px[x, y]
              for x in range(x0 + mx, x1 - mx + 1)
              for y in range(y0 + my, y1 - my + 1)]
    if not pixels:
        pixels = [px[(x0 + x1) // 2, (y0 + y1) // 2]]
    return tuple(statistics.median(p[i] for p in pixels) for i in range(3))


def extract_grid(im):
    px = im.load()
    xs, ys = detect_grid(im)
    if len(xs) < 2 or len(ys) < 2:
        return None
    return [[to_hex(sample_cell(px, x0, x1, y0, y1)) for x0, x1 in xs]
            for y0, y1 in ys]


def extract_dominant(im, n):
    q = im.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: n * 3]
    counts = dict(q.getcolors(n * 2) or [])
    entries = [(counts.get(i, 0), to_hex(pal[i * 3:i * 3 + 3])) for i in range(n)]
    entries.sort(key=lambda e: -e[0])
    return [h for _, h in entries]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--mode", choices=("auto", "grid", "dominant"), default="auto")
    ap.add_argument("--colors", type=int, default=16,
                    help="how many colours in dominant mode (default 16)")
    ap.add_argument("--json", metavar="PATH", help="also write the result as JSON")
    args = ap.parse_args()

    im = Image.open(args.image).convert("RGB")

    grid = None
    if args.mode in ("auto", "grid"):
        grid = extract_grid(im)
        if grid is None and args.mode == "grid":
            sys.exit("no grid found — try --mode dominant")

    if grid:
        rows, cols = len(grid), len(grid[0])
        print(f"grid mode: {cols} x {rows} = {rows * cols} swatches"
              f"  ({args.image}, {im.width}x{im.height})")
        for i, row in enumerate(grid, 1):
            print(f"{i:3d}  " + "  ".join(row))
        flat = [c for row in grid for c in row]
        print(f"\n{len(flat)} swatches, {len(set(flat))} unique")
        if cols == 5:
            print("note: 5 columns — each row maps straight onto a preset "
                  "palette ramp (shades 1-5).")
        result = grid
    else:
        colors = extract_dominant(im, args.colors)
        print(f"dominant mode: {len(colors)} colours, most common first"
              f"  ({args.image}, {im.width}x{im.height})")
        for i, c in enumerate(colors, 1):
            print(f"{i:3d}  {c}")
        result = colors

    if args.json:
        with open(args.json, "w") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
