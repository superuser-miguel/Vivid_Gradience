# custom_themes.py
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

"""The user's theme library under ~/.local/share/themes.

Two jobs: list and manage what is installed there, and give a *foreign*
gtk.css somewhere to go. When Apply finds a stylesheet Vivid Gradience did
not write, the right move is not a backup the user will never look at — it
is turning the file into a selectable theme in this library ("rescue,
don't just back up"). ~/.local/share/themes is also a Flatpak default
grant, so one name resolves for host and sandboxed applications alike.
"""

import os
import shutil

from datetime import date

from gi.repository import GLib

from gradience.backend.globals import get_gtk_theme_dir
from gradience.backend.logger import Logger

logging = Logger()

THEMES_DIR = os.path.join(GLib.get_home_dir(), ".local", "share", "themes")

# Subdirectories that tell us what a theme actually provides.
PROVIDES = ("gtk-4.0", "gtk-3.0", "gtk-2.0", "gnome-shell")


def list_themes() -> list:
    """Every theme directory, with what it provides. Sorted by name."""
    if not os.path.isdir(THEMES_DIR):
        return []

    themes = []
    for name in sorted(os.listdir(THEMES_DIR), key=str.casefold):
        path = os.path.join(THEMES_DIR, name)
        if not os.path.isdir(path):
            continue
        provides = [d for d in PROVIDES if os.path.isdir(os.path.join(path, d))]
        themes.append({"name": name, "path": path, "provides": provides})
    return themes


def _free_name(base: str) -> str:
    candidate, n = base, 2
    while os.path.exists(os.path.join(THEMES_DIR, candidate)):
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def rescue_stylesheet(app_type: str) -> str:
    """Move a foreign gtk.css (and its assets) into the theme library.

    Returns the created theme name. The file is moved, not copied — after a
    rescue the config dir is clear for Apply to write, and the user's theme
    lives on as ~/.local/share/themes/<name>/<toolkit>/gtk.css.
    """
    theme_dir = get_gtk_theme_dir(app_type)
    css_path = os.path.join(theme_dir, "gtk.css")
    assets_path = os.path.join(theme_dir, "assets")

    if not os.path.isfile(css_path):
        raise FileNotFoundError(f"nothing to rescue at {css_path}")

    toolkit = "gtk-4.0" if app_type == "gtk4" else "gtk-3.0"
    name = _free_name(f"imported-{app_type}-{date.today().isoformat()}")
    dest_dir = os.path.join(THEMES_DIR, name, toolkit)
    os.makedirs(dest_dir, exist_ok=True)

    shutil.move(css_path, os.path.join(dest_dir, "gtk.css"))
    if os.path.isdir(assets_path):
        shutil.move(assets_path, os.path.join(dest_dir, "assets"))

    with open(os.path.join(THEMES_DIR, name, "README"), "w",
              encoding="utf-8") as f:
        f.write(
            f"Imported by Vivid Gradience on {date.today().isoformat()}.\n"
            f"This was the stylesheet found at {css_path} before a preset\n"
            "was first applied. It was moved here so it stays selectable\n"
            "instead of being overwritten.\n")

    logging.debug(f"Rescued {css_path} into theme {name!r}")
    return name


def import_theme(source_dir: str) -> str:
    """Copy a theme directory into the library. Returns the theme name."""
    if not os.path.isdir(source_dir):
        raise NotADirectoryError(source_dir)

    name = _free_name(os.path.basename(os.path.normpath(source_dir)))
    shutil.copytree(source_dir, os.path.join(THEMES_DIR, name))
    logging.debug(f"Imported theme {name!r} from {source_dir}")
    return name


def remove_theme(name: str) -> None:
    """Delete one theme from the library. Refuses to reach outside it."""
    path = os.path.realpath(os.path.join(THEMES_DIR, name))
    if os.path.dirname(path) != os.path.realpath(THEMES_DIR):
        raise ValueError(f"{name!r} is not directly inside {THEMES_DIR}")
    shutil.rmtree(path)
    logging.debug(f"Removed theme {name!r}")
