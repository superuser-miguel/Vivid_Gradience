#!/usr/bin/env python3
"""Cross-check the Firefox engine against the pinned firefox-gnome-theme.

The engine and the theme meet at two seams, and both can break in total
silence when the pin moves:

  variables   The engine writes --gnome-* CSS variables; the theme reads
              them. A variable the theme stopped reading means a colour
              that stops landing with no error anywhere — eleven such
              variables were found by hand when the pin moved to v150.

  prefs       The theme's optional features answer to gnomeTheme.* prefs;
              the app exposes them as switches from a schema. A pref the
              release reads and the schema omits is a feature no one can
              reach; a schema entry the release ignores is a switch that
              does nothing.

This makes the check one command. It parses the engine's stylesheet
templates and the options schema out of the source, takes the pinned
release from the same cache the app installs from, and diffs the two
sides. Exit 0 when every check passes, 1 otherwise — so it can gate a
pin move mechanically.

The pinned tree is looked for in the app's cache (host and Flatpak paths),
then any profile carrying our stamp at the right tag. --fetch downloads
the release into the host cache if none of those has it.

Usage:
  tools/check-firefox-pin.py                 # check the current pin
  tools/check-firefox-pin.py --tag v151      # try a candidate before moving the pin
  tools/check-firefox-pin.py --theme-dir ~/src/firefox-gnome-theme
  tools/check-firefox-pin.py --fetch         # allow a network download
"""
import argparse
import io
import os
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / "gradience/backend/theming/firefox.py"
INSTALLER = REPO / "gradience/backend/theming/firefox_installer.py"
SCHEMA = REPO / "gradience/frontend/schemas/firefox_options_schema.py"

ARCHIVE_URL = ("https://github.com/rafaelmardojai/firefox-gnome-theme"
               "/archive/refs/tags/{tag}.tar.gz")
STAMP_NAME = ".vivid-gradience-managed"

# The definition/read surface of the *theme*: its stylesheets, not its
# install scripts or the user.js template (those mention prefs they write,
# which is not the same as a feature reading them).
THEME_CSS_GLOBS = ("theme/**/*.css", "userChrome.css", "userContent.css",
                   "customChrome.css", "customContent.css")

VAR_WRITE = re.compile(r"^\s*(--gnome-[a-z0-9-]+)\s*:", re.M)
VAR_READ = re.compile(r"var\(\s*(--gnome-[a-z0-9-]+)")
PREF = re.compile(r"gnomeTheme\.[A-Za-z][A-Za-z.]*")


def pinned_tag():
    m = re.search(r'^PINNED_TAG = "([^"]+)"', INSTALLER.read_text(), re.M)
    if not m:
        sys.exit(f"cannot find PINNED_TAG in {INSTALLER}")
    return m.group(1)


def find_theme_tree(tag, fetch_ok):
    """The pinned release's tree: cache, then stamped profiles, then network."""
    candidates = [
        Path.home() / ".cache/gradience/firefox-gnome-theme" / tag,
        Path.home() / ".var/app/io.github.superuser_miguel.VividGradience"
                      "/cache/gradience/firefox-gnome-theme" / tag,
    ]
    for c in candidates:
        if (c / "userChrome.css").is_file():
            return c, f"cache ({c})"

    for profiles in (Path.home() / ".mozilla/firefox",
                     Path.home() / ".librewolf"):
        if not profiles.is_dir():
            continue
        for prof in sorted(profiles.iterdir()):
            tree = prof / "chrome/firefox-gnome-theme"
            stamp = tree / STAMP_NAME
            if stamp.is_file() and stamp.read_text().splitlines()[0].strip() == tag:
                return tree, f"stamped install ({prof.name})"

    if not fetch_ok:
        sys.exit(f"no local copy of {tag} (checked cache and stamped "
                 f"profiles) — rerun with --fetch to download it")

    url = ARCHIVE_URL.format(tag=tag)
    print(f"fetching {url}")
    with urllib.request.urlopen(url) as r:
        body = r.read()
    dest = candidates[0]
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as tar:
        for member in tar.getmembers():
            parts = member.path.split("/", 1)
            if len(parts) < 2 or not parts[1]:
                continue
            member.path = parts[1]
            tar.extract(member, dest, filter="data")
    if not (dest / "userChrome.css").is_file():
        sys.exit("downloaded archive does not look like firefox-gnome-theme")
    return dest, f"downloaded ({dest})"


def theme_css_text(tree):
    text = []
    for pattern in THEME_CSS_GLOBS:
        for p in sorted(tree.glob(pattern)):
            text.append(p.read_text(errors="replace"))
    if not text:
        sys.exit(f"no stylesheets found under {tree}")
    return "\n".join(text)


def check(title, bad, detail):
    if bad:
        print(f"  FAIL {title}:")
        for item in sorted(bad):
            print(f"       {item}  ({detail})")
    else:
        print(f"  ok   {title}")
    return len(bad)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", help="check against this release instead of the pin")
    ap.add_argument("--theme-dir", type=Path,
                    help="use this theme tree instead of locating one")
    ap.add_argument("--fetch", action="store_true",
                    help="allow downloading the release if no local copy exists")
    args = ap.parse_args()

    pin = pinned_tag()
    tag = args.tag or pin
    if args.theme_dir:
        tree, origin = args.theme_dir, "given on the command line"
        if not (tree / "userChrome.css").is_file():
            sys.exit(f"{tree} does not look like firefox-gnome-theme")
    else:
        tree, origin = find_theme_tree(tag, args.fetch)

    engine_src = ENGINE.read_text()
    writes = set(VAR_WRITE.findall(engine_src))
    our_reads = set(VAR_READ.findall(engine_src))
    theme_css = theme_css_text(tree)
    theme_reads = set(VAR_READ.findall(theme_css))
    theme_writes = set(VAR_WRITE.findall(theme_css))

    theme_prefs = set(PREF.findall(theme_css))
    schema_prefs = set(re.findall(r'"pref":\s*"(gnomeTheme\.[^"]+)"',
                                  SCHEMA.read_text()))

    label = tag if tag == pin else f"{tag} (pin is {pin})"
    print(f"engine vs firefox-gnome-theme {label} — {origin}")
    print(f"  {len(writes)} variables written, {len(schema_prefs)} prefs in "
          f"the schema; theme reads {len(theme_reads)} variables, "
          f"{len(theme_prefs)} prefs")

    failures = 0
    failures += check("every variable the engine writes is read by the theme",
                      writes - theme_reads,
                      "written by the engine, read nowhere in the release — "
                      "the colour never lands")
    failures += check("every variable the engine references is defined",
                      our_reads - writes - theme_writes,
                      "var() with no definition on either side — a typo or "
                      "a removed variable")
    failures += check("every pref the theme reads has a switch",
                      theme_prefs - schema_prefs,
                      "feature in the release, absent from "
                      "firefox_options_schema.py — unreachable from the app")
    failures += check("every switch matches a pref the theme reads",
                      schema_prefs - theme_prefs,
                      "in the schema, read nowhere in the release — "
                      "a switch that does nothing")

    if failures:
        print(f"\n{failures} problem(s) — do not move the pin until resolved")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
