# firefox_installer.py
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

import io
import os
import re
import shutil
import tarfile

from pathlib import Path

import gi

gi.require_version("Soup", "3.0")
from gi.repository import GLib, Soup

from gradience.backend.globals import user_cache_dir
from gradience.backend.logger import Logger

logging = Logger()

# The one exception to report-don't-install: firefox-gnome-theme is not a
# system component but plain files inside the user's Firefox profile — a
# directory this engine already writes to. System-level prerequisites (the
# User Themes extension, the Gtk3theme Flatpak) stay report-only.
#
# Pinned, not chased: upstream occasionally changes required prefs between
# Firefox versions, so the app installs a release we have tried, and the pin
# moves at our own release cadence — never silently at the user's expense.
PINNED_TAG = "v150"
ARCHIVE_URL = ("https://github.com/rafaelmardojai/firefox-gnome-theme"
               "/archive/refs/tags/{tag}.tar.gz")

THEME_DIR_NAME = "firefox-gnome-theme"

# Installs we made carry this stamp (holding the installed tag). A theme
# directory without it is the user's own checkout: never updated, never
# uninstalled, never written to except the customChrome.css hook the theme
# itself designates for user changes.
STAMP_NAME = ".vivid-gradience-managed"

CSS_MARKER = "Generated with Vivid Gradience"

# user.js additions live between these fences. Everything outside them is
# the user's own configuration and is never rewritten or deleted — appending
# our block last means our prefs win without erasing theirs (user.js is
# applied top to bottom).
USERJS_BEGIN = ("// >>> Vivid Gradience: firefox-gnome-theme preferences. "
                "Do not edit inside this block.")
USERJS_END = "// <<< Vivid Gradience: end of firefox-gnome-theme preferences."

# The theme's optional features get a fence of their own, after the required
# prefs. Two blocks rather than one because they answer to different things:
# the required prefs come from the release we install and change when the pin
# moves, these come from the user and must survive an update.
OPTIONS_BEGIN = ("// >>> Vivid Gradience: firefox-gnome-theme options. "
                 "Change these in the app rather than here.")
OPTIONS_END = "// <<< Vivid Gradience: end of firefox-gnome-theme options."

PREF_RE = re.compile(r'user_pref\(\s*"([^"]+)"\s*,\s*(true|false)\s*\)')


class FirefoxThemeInstaller:
    """Fetch, install, update and uninstall firefox-gnome-theme in Firefox
    profiles, exactly as upstream's install.sh would — but only ever in
    installs stamped as ours."""

    def __init__(self):
        self.cache_dir = Path(user_cache_dir) / "gradience" / THEME_DIR_NAME

    # -- state ---------------------------------------------------------------

    def theme_dir(self, profile):
        return Path(profile) / "chrome" / THEME_DIR_NAME

    def installed_tag(self, profile):
        """The pinned tag our stamp records, or None if the install is not
        ours (including the user's own checkouts)."""
        try:
            stamp = (self.theme_dir(profile) / STAMP_NAME).read_text()
        except OSError:
            return None
        return stamp.splitlines()[0].strip() if stamp.strip() else None

    def is_managed(self, profile):
        return self.installed_tag(profile) is not None

    def plan(self, profiles):
        """Split profiles into (missing, stale, foreign): no theme at all,
        our install behind the pin, and installs that are not ours."""
        missing, stale, foreign = [], [], []
        for profile in profiles:
            if not self.theme_dir(profile).is_dir():
                missing.append(profile)
                continue
            tag = self.installed_tag(profile)
            if tag is None:
                foreign.append(profile)
            elif tag != PINNED_TAG:
                stale.append(profile)
        return missing, stale, foreign

    # -- fetch ---------------------------------------------------------------

    def fetch(self, tag=PINNED_TAG):
        """Return a local tree of the tagged release, downloading it once and
        serving every later install from the cache."""
        dest = self.cache_dir / tag
        if (dest / "userChrome.css").is_file():
            return dest

        url = ARCHIVE_URL.format(tag=tag)
        logging.debug(f"Fetching {url}")
        session = Soup.Session()
        message = Soup.Message.new("GET", url)
        try:
            body = session.send_and_read(message, None)
        except GLib.GError as e:
            logging.error("Failed to download firefox-gnome-theme.", exc=e)
            raise
        if message.get_status() != Soup.Status.OK:
            raise OSError(
                f"Download of {url} failed with HTTP {message.get_status()}")

        tmp = self.cache_dir / f".tmp-{tag}"
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        # GitHub archives nest everything under one release-named directory;
        # strip it so the cache holds the theme tree itself.
        with tarfile.open(fileobj=io.BytesIO(body.get_data()),
                          mode="r:gz") as tar:
            for member in tar.getmembers():
                parts = member.path.split("/", 1)
                if len(parts) < 2 or not parts[1]:
                    continue
                member.path = parts[1]
                tar.extract(member, tmp, filter="data")
        if not (tmp / "userChrome.css").is_file():
            shutil.rmtree(tmp)
            raise OSError("Downloaded archive does not look like "
                          "firefox-gnome-theme (no userChrome.css).")
        os.replace(tmp, dest)
        logging.debug(f"Cached firefox-gnome-theme {tag} at {dest}")
        return dest

    # -- install / update ----------------------------------------------------

    def install(self, profile, tree, tag=PINNED_TAG):
        """Install (or update) the theme into one profile and wire it up.
        Refuses a theme directory that exists without our stamp."""
        profile = Path(profile)
        target = self.theme_dir(profile)
        if target.is_dir() and not self.is_managed(profile):
            raise OSError(f"{target} exists but was not installed by us")

        # A managed update replaces the tree wholesale, so stale files from
        # the previous release cannot linger. customChrome.css goes with it;
        # the caller reapplies the preset afterwards.
        if target.is_dir():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(tree, target)
        (target / STAMP_NAME).write_text(
            f"{tag}\n"
            "Installed by Vivid Gradience from\n"
            "https://github.com/rafaelmardojai/firefox-gnome-theme\n"
            "Remove this file and the app will treat the install as yours.\n")

        self._wire_import(profile / "chrome" / "userChrome.css",
                          "userChrome.css")
        self._wire_import(profile / "chrome" / "userContent.css",
                          "userContent.css")
        self._wire_prefs(profile, target)
        logging.debug(f"Installed firefox-gnome-theme {tag} into {profile}")

    def _wire_import(self, path, css_name):
        """Put the theme's @import first in the user stylesheet, as upstream
        requires (imports must precede other rules). A pre-existing import —
        the user's own wiring — is left exactly as it is."""
        our_line = (f'@import "{THEME_DIR_NAME}/{css_name}"; '
                    f"/* {CSS_MARKER} */")
        try:
            content = path.read_text()
        except OSError:
            content = ""
        if f"{THEME_DIR_NAME}/{css_name}" in content:
            return
        path.write_text(our_line + "\n" + content)

    def _wire_prefs(self, profile, theme_dir):
        """Append the theme's required prefs to the profile's user.js inside
        our fences, replacing only a previous block of ours."""
        conf = theme_dir / "configuration" / "user.js"
        try:
            prefs = [line.strip() for line in conf.read_text().splitlines()
                     if line.strip().startswith("user_pref")]
        except OSError:
            prefs = []
        if not prefs:
            logging.warning(f"No prefs found in {conf}; user.js not touched.")
            return

        userjs = Path(profile) / "user.js"
        try:
            content = userjs.read_text()
        except OSError:
            content = ""
        content = self._strip_block(content)
        block = "\n".join([USERJS_BEGIN, *prefs, USERJS_END])
        if content and not content.endswith("\n"):
            content += "\n"
        userjs.write_text(content + block + "\n")

    # -- options -------------------------------------------------------------

    def read_options(self, profile, prefs):
        """What each of `prefs` currently evaluates to in a profile. Firefox
        reads user.js top to bottom and the last assignment wins, so that is
        what we report — including lines the user wrote themselves outside
        our fences. Anything unset is off, which is the theme's default."""
        try:
            content = (Path(profile) / "user.js").read_text()
        except OSError:
            content = ""
        values = {pref: False for pref in prefs}
        for name, value in PREF_RE.findall(content):
            if name in values:
                values[name] = value == "true"
        return values

    def write_options(self, profile, options):
        """Write every managed option into the options fence, replacing only
        a previous block of ours.

        The block is written whole, including the options that are off, so
        that turning one off actually overrides an earlier line rather than
        silently deferring to it. That only stays honest because the app
        seeds its switches from read_options() first: what we write back is
        what the profile already said, plus the one thing that changed."""
        userjs = Path(profile) / "user.js"
        try:
            content = userjs.read_text()
        except OSError:
            content = ""
        content = self._strip_block(content, OPTIONS_BEGIN, OPTIONS_END)
        lines = [f'user_pref("{pref}", {"true" if on else "false"});'
                 for pref, on in options.items()]
        block = "\n".join([OPTIONS_BEGIN, *lines, OPTIONS_END])
        if content and not content.endswith("\n"):
            content += "\n"
        userjs.write_text(content + block + "\n")

    # -- uninstall -----------------------------------------------------------

    def uninstall(self, profile):
        """Take a managed install out completely: the theme tree, our import
        lines, our user.js block. Anything we did not write stays."""
        profile = Path(profile)
        if not self.is_managed(profile):
            return False
        shutil.rmtree(self.theme_dir(profile))

        for css_name in ("userChrome.css", "userContent.css"):
            path = profile / "chrome" / css_name
            try:
                lines = path.read_text().splitlines()
            except OSError:
                continue
            kept = [line for line in lines
                    if not (THEME_DIR_NAME in line and CSS_MARKER in line)]
            if any(line.strip() for line in kept):
                path.write_text("\n".join(kept) + "\n")
            else:
                path.unlink()

        userjs = profile / "user.js"
        try:
            content = self._strip_block(userjs.read_text())
            content = self._strip_block(content, OPTIONS_BEGIN, OPTIONS_END)
        except OSError:
            content = None
        if content is not None:
            if content.strip():
                userjs.write_text(content)
            else:
                userjs.unlink()

        logging.debug(f"Uninstalled firefox-gnome-theme from {profile}")
        return True

    @staticmethod
    def _strip_block(content, begin=USERJS_BEGIN, end=USERJS_END):
        lines, keeping = [], True
        for line in content.splitlines():
            if line.strip() == begin.strip():
                keeping = False
                continue
            if line.strip() == end.strip():
                keeping = True
                continue
            if keeping:
                lines.append(line)
        result = "\n".join(lines)
        if result and not result.endswith("\n"):
            result += "\n"
        return result
