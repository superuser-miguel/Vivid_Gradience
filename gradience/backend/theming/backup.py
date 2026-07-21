# backup.py
#
# Change the look of Adwaita, with ease
# Copyright (C) 2022-2026, Gradience Team
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

"""Versioned backups of the stylesheets we overwrite.

Applying a preset replaces ``~/.config/gtk-{3.0,4.0}/gtk.css`` wholesale. If the
user had a full GTK theme installed there (Matcha, Gruvbox-GTK-Theme and friends
ship one, assets and all), that file is the theme — overwriting it destroys it.

This module keeps plain, user-inspectable copies so nothing is lost:

    backups/<app_type>/
        original/                  captured once, never overwritten
            gtk.css  assets/  meta.json
        snapshots/<timestamp>/     rotated, newest is "previous"
            gtk.css  assets/  meta.json

Deliberately not a git repo: the runtime ships no git, the data is a handful of
copies of one small file, and a folder the user can open in Files is far easier
to recover from by hand than a repo inside a sandbox.
"""

import os
import json
import shutil
import hashlib

from datetime import datetime, timezone

from gradience.backend.globals import user_data_dir, get_gtk_theme_dir

from gradience.backend.logger import Logger

logging = Logger()


# How many rotating snapshots to keep per app type. `original/` is never
# included in this count and is never rotated away.
MAX_SNAPSHOTS = 10

TIMESTAMP_FORMAT = "%Y-%m-%dT%H-%M-%S"

# Marker written into every stylesheet we generate. Its absence in a file that
# references assets means someone else's theme is installed there.
GENERATED_MARKER = "Generated with"


class ThemeBackup:
    """Snapshot store for one app type ("gtk4" or "gtk3")."""

    def __init__(self, app_type: str):
        self.app_type = app_type
        self.theme_dir = get_gtk_theme_dir(app_type)
        self.css_path = os.path.join(self.theme_dir, "gtk.css")
        self.assets_path = os.path.join(self.theme_dir, "assets")

        self.root = os.path.join(user_data_dir, "gradience", "backups", app_type)
        self.original_dir = os.path.join(self.root, "original")
        self.snapshots_dir = os.path.join(self.root, "snapshots")

    # -- inspection ------------------------------------------------------

    def describe_current(self) -> dict:
        """Classify whatever currently sits in the theme dir.

        ``kind`` is one of "missing", "ours" or "foreign". A foreign stylesheet
        is one we did not generate — most importantly a full installed theme,
        which is the case worth warning about before we replace it.
        """
        if not os.path.exists(self.css_path):
            return {"kind": "missing", "size": 0, "has_assets": False}

        try:
            with open(self.css_path, "r", encoding="utf-8") as f:
                contents = f.read()
        except OSError as e:
            logging.error(f"Could not read {self.css_path}.", exc=e)
            return {"kind": "missing", "size": 0, "has_assets": False}

        has_assets = os.path.isdir(self.assets_path)
        generated = GENERATED_MARKER in contents

        return {
            "kind": "ours" if generated else "foreign",
            "size": len(contents.encode("utf-8")),
            "has_assets": has_assets,
            "asset_refs": contents.count("assets/"),
        }

    def has_original(self) -> bool:
        return os.path.exists(os.path.join(self.original_dir, "gtk.css"))

    def original_meta(self) -> dict:
        """Metadata for the stored original, or an empty dict if there is none."""
        if not self.has_original():
            return {}

        return self._read_meta(self.original_dir)

    def list_snapshots(self) -> list:
        """Newest first. Each entry carries its stored metadata."""
        if not os.path.isdir(self.snapshots_dir):
            return []

        entries = []
        for name in sorted(os.listdir(self.snapshots_dir), reverse=True):
            path = os.path.join(self.snapshots_dir, name)
            if not os.path.isdir(path):
                continue
            entries.append({"name": name, "path": path, "meta": self._read_meta(path)})

        return entries

    def previous(self) -> dict:
        snapshots = self.list_snapshots()
        return snapshots[0] if snapshots else None

    # -- capture ---------------------------------------------------------

    def capture(self, applied_preset: str = None) -> dict:
        """Back up the current stylesheet before it gets overwritten.

        The first capture also seeds ``original/``, so the user's pre-Gradience
        state survives no matter how many presets they apply afterwards.
        Returns the snapshot metadata, or None when there was nothing to save.
        """
        state = self.describe_current()
        if state["kind"] == "missing":
            return None

        if not self.has_original():
            self._store(self.original_dir, state, applied_preset, is_original=True)
            logging.debug(f"Seeded original {self.app_type} backup ({state['kind']}).")

        timestamp = datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)
        target = os.path.join(self.snapshots_dir, timestamp)

        # A second Apply inside the same second would otherwise collide.
        suffix = 1
        while os.path.exists(target):
            target = os.path.join(self.snapshots_dir, f"{timestamp}-{suffix}")
            suffix += 1

        meta = self._store(target, state, applied_preset)
        self._rotate()

        return meta

    def _store(self, target: str, state: dict, applied_preset, is_original=False) -> dict:
        os.makedirs(target, exist_ok=True)
        shutil.copy2(self.css_path, os.path.join(target, "gtk.css"))

        # We never write assets ourselves, so they only change when a foreign
        # theme is installed. Copying 200-odd PNGs on every Apply would be
        # waste — only store them when they differ from what we already hold.
        assets_digest = self._assets_digest()
        if state["has_assets"] and assets_digest != self._newest_assets_digest():
            shutil.copytree(
                self.assets_path,
                os.path.join(target, "assets"),
                dirs_exist_ok=True,
            )

        meta = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "app_type": self.app_type,
            "kind": state["kind"],
            "size": state["size"],
            "has_assets": state["has_assets"],
            "assets_digest": assets_digest,
            "applied_preset": applied_preset,
            "is_original": is_original,
        }

        with open(os.path.join(target, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        return meta

    def _rotate(self) -> None:
        snapshots = self.list_snapshots()
        for stale in snapshots[MAX_SNAPSHOTS:]:
            try:
                shutil.rmtree(stale["path"])
            except OSError as e:
                logging.warning(f"Could not rotate away {stale['path']}: {e}")

    # -- restore ---------------------------------------------------------

    def restore(self, source: str) -> None:
        """Copy a stored snapshot back over the live stylesheet.

        ``source`` is a snapshot directory, or the string "original".
        """
        if source == "original":
            source = self.original_dir

        css = os.path.join(source, "gtk.css")
        if not os.path.exists(css):
            raise FileNotFoundError(f"No stylesheet stored in {source}")

        os.makedirs(self.theme_dir, exist_ok=True)

        # Save what we're about to replace, so restoring is itself undoable.
        self.capture(applied_preset=None)

        shutil.copy2(css, self.css_path)

        stored_assets = os.path.join(source, "assets")
        if os.path.isdir(stored_assets):
            shutil.copytree(stored_assets, self.assets_path, dirs_exist_ok=True)
        else:
            # The snapshot shared its assets with an earlier one; fall back to
            # the original, which always holds a full copy when assets exist.
            original_assets = os.path.join(self.original_dir, "assets")
            if os.path.isdir(original_assets) and not os.path.isdir(self.assets_path):
                shutil.copytree(original_assets, self.assets_path, dirs_exist_ok=True)

        logging.debug(f"Restored {self.app_type} stylesheet from {source}.")

    # -- helpers ---------------------------------------------------------

    def _read_meta(self, path: str) -> dict:
        try:
            with open(os.path.join(path, "meta.json"), "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def _assets_digest(self) -> str:
        """Cheap fingerprint of the assets dir — names, sizes and mtimes."""
        if not os.path.isdir(self.assets_path):
            return ""

        digest = hashlib.sha256()
        for root, dirs, files in os.walk(self.assets_path):
            dirs.sort()
            for name in sorted(files):
                full = os.path.join(root, name)
                try:
                    stat = os.stat(full)
                except OSError:
                    continue
                rel = os.path.relpath(full, self.assets_path)
                digest.update(f"{rel}:{stat.st_size}:{int(stat.st_mtime)}".encode("utf-8"))

        return digest.hexdigest()

    def _newest_assets_digest(self) -> str:
        for entry in self.list_snapshots():
            stored = entry["meta"].get("assets_digest")
            if stored:
                return stored

        return self._read_meta(self.original_dir).get("assets_digest", "")
