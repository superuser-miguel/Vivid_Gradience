# firefox.py
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

import re

from pathlib import Path
from configparser import ConfigParser, Error as ConfigParserError

from gradience.backend.logger import Logger

logging = Logger()

# The customChrome.css hook is firefox-gnome-theme's API for user overrides.
# It is the user's file, not the theme's: it may hold their own CSS. The
# marker fences our claim — a customChrome.css without it is someone else's
# work and is never overwritten (see the stylesheet-ownership principles).
MARKER = "Generated with Vivid Gradience"

TEMPLATE = """/* {marker}
 *
 * Written by the Firefox engine from the preset's colours. Reapplying a
 * preset rewrites this file; delete it (or Reset in the app) to fall back
 * to firefox-gnome-theme's own colours. Requires
 * https://github.com/rafaelmardojai/firefox-gnome-theme in this profile.
 */

/* Only variables the pinned release actually reads. The theme drops and
 * renames these between versions, and one it no longer reads is a colour
 * the preset silently stops reaching — so when the pin moves, check this
 * list against the release rather than assuming it still lands. */
:root {{
    --gnome-window-background:                     {window_bg_color};
    --gnome-accent-bg:                             {accent_bg_color};
    --gnome-accent:                                {accent_color};
    --gnome-toolbar-background:                    {window_bg_color};
    --gnome-toolbar-icon-fill:                     {window_fg_color};
    --gnome-menu-background:                       {popover_bg_color};
    --gnome-headerbar-background:                  {headerbar_bg_color};
    --gnome-entry-color:                           {view_fg_color};
    --gnome-inactive-entry-color:                  {view_fg_color};

    /* Tab overlays derive from the preset's own foreground, so they darken a
     * light scheme and lighten a dark one. The plugin this replaces wrote
     * white literals here, which vanished on light presets. */
    --gnome-tabbar-tab-hover-background:           {fg_025};
    --gnome-tabbar-tab-active-background:          {fg_075};
    --gnome-tabbar-tab-active-hover-background:    {fg_100};
    --gnome-tabbar-tab-active-background-contrast: {fg_125};
}}

/* about:home and about:newtab, from the same preset roles as everything
 * else — the plugin this replaces wrote Firefox's stock dark palette here
 * as literals, so the new-tab page ignored the scheme entirely. */
@-moz-document url-prefix(about:home), url-prefix(about:newtab) {{
 body{{
  --newtab-background-color: {window_bg_color}!important;
  --newtab-border-primary-color: {fg_80}!important;
  --newtab-border-secondary-color: {fg_10}!important;
  --newtab-button-primary-color: {accent_bg_color}!important;
  --newtab-button-secondary-color: {card_bg_color}!important;
  --newtab-element-active-color: {fg_20}!important;
  --newtab-element-hover-color: {fg_10}!important;
  --newtab-icon-primary-color: {fg_80}!important;
  --newtab-icon-secondary-color: {fg_40}!important;
  --newtab-icon-tertiary-color: {fg_40}!important;
  --newtab-inner-box-shadow-color: {fg_20}!important;
  --newtab-link-primary-color: var(--gnome-accent)!important;
  --newtab-link-secondary-color: {accent_color}!important;
  --newtab-text-conditional-color: {window_fg_color}!important;
  --newtab-text-primary-color: {window_fg_color}!important;
  --newtab-text-secondary-color: {fg_80}!important;
  --newtab-textbox-background-color: var(--gnome-toolbar-background)!important;
  --newtab-textbox-border: {headerbar_border_color}!important;
  --newtab-textbox-focus-color: {accent_bg_color}!important;
  --newtab-textbox-focus-boxshadow: 0 0 0 1px {accent_bg_color}, 0 0 0 4px {accent_30}!important;
  --newtab-feed-button-background: {card_bg_color}!important;
  --newtab-feed-button-text: {window_fg_color}!important;
  --newtab-feed-button-background-faded: {card_60}!important;
  --newtab-feed-button-text-faded: {fg_00}!important;
  --newtab-feed-button-spinner: {fg_80}!important;
  --newtab-contextmenu-background-color: {popover_bg_color}!important;
  --newtab-contextmenu-button-color: {window_bg_color}!important;
  --newtab-modal-color: {dialog_bg_color}!important;
  --newtab-overlay-color: rgba(12, 12, 13, 0.8)!important;
  --newtab-section-header-text-color: {fg_80}!important;
  --newtab-section-navigation-text-color: {fg_80}!important;
  --newtab-section-active-contextmenu-color: {window_fg_color}!important;
  --newtab-search-border-color: {fg_20}!important;
  --newtab-search-dropdown-color: {card_bg_color}!important;
  --newtab-search-dropdown-header-color: {dialog_bg_color}!important;
  --newtab-search-header-background-color: {window_95}!important;
  --newtab-search-icon-color: {fg_60}!important;
  --newtab-search-wordmark-color: {window_fg_color}!important;
  --newtab-topsites-background-color: {card_bg_color}!important;
  --newtab-topsites-icon-shadow: none!important;
  --newtab-topsites-label-color: {fg_80}!important;
  --newtab-card-active-outline-color: var(--gnome-toolbar-icon-fill)!important;
  --newtab-card-background-color: var(--gnome-toolbar-background)!important;
  --newtab-card-hairline-color: {fg_10}!important;
  --newtab-card-placeholder-color: {card_bg_color}!important;
  --newtab-card-shadow: 0 1px 8px 0 rgba(12, 12, 13, 0.2)!important;
  --newtab-snippets-background-color: {card_bg_color}!important;
  --newtab-snippets-hairline-color: {fg_10}!important;
  --trailhead-header-text-color: {fg_60}!important;
  --trailhead-cards-background-color: rgba(12, 12, 13, 0.1)!important;
  --trailhead-card-button-background-color: rgba(12, 12, 13, 0.3)!important;
  --trailhead-card-button-background-hover-color: rgba(12, 12, 13, 0.5)!important;
  --trailhead-card-button-background-active-color: rgba(12, 12, 13, 0.7)!important;
 }}
}}

/* Tab group swatches.
 *
 * Firefox draws a group's chicklet as the icon of a .subviewbutton-iconic —
 * an ordinary .toolbarbutton-icon — and colours it per group through
 * --menuitem-icon-fill, with the outline coming from the parent's stroke.
 * firefox-gnome-theme tints every .toolbarbutton-icon with
 * --gnome-toolbar-icon-fill !important and narrows -moz-context-properties
 * to fill alone, so from a user sheet it outranks Firefox's own colour: all
 * groups flatten to the toolbar icon colour and the outline disappears,
 * which hides saved groups entirely. Firefox still hands us the right value,
 * so give the swatch its context properties back and defer to it. */
.tab-group-icon.tab-group-icon.tab-group-icon > .toolbarbutton-icon {{
    -moz-context-properties: fill, stroke !important;
    fill: var(--menuitem-icon-fill,
              light-dark(var(--tab-group-color),
                         var(--tab-group-color-invert))) !important;
}}
"""


def _parse_rgb(color):
    """'#rgb', '#rrggbb' or 'rgb[a](...)' -> (r, g, b) ints, or None."""
    color = color.strip()
    m = re.match(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)", color)
    if m:
        return tuple(min(255, int(float(v))) for v in m.groups())
    m = re.match(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", color)
    if not m:
        return None
    hexpart = m.group(1)
    if len(hexpart) == 3:
        hexpart = "".join(c * 2 for c in hexpart)
    return tuple(int(hexpart[i:i + 2], 16) for i in (0, 2, 4))


def _alpha(color, alpha, fallback="#808080"):
    rgb = _parse_rgb(color) or _parse_rgb(fallback)
    return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})"


class FirefoxTheme:
    """Write the current preset into firefox-gnome-theme's customChrome.css
    hook, per profile, for every browser the Flatpak is granted."""

    BROWSER_DIRS = [
        "~/.mozilla/firefox",
        "~/.librewolf",
        "~/.waterfox",
        "~/.var/app/org.mozilla.firefox/.mozilla/firefox",
        "~/.var/app/io.gitlab.librewolf-community/.librewolf",
        "~/.var/app/net.waterfox.waterfox/.waterfox",
        "~/snap/firefox/common/.mozilla/firefox",
    ]

    THEME_DIR_NAME = "firefox-gnome-theme"

    def find_profiles(self):
        """Every profile listed by an existing profiles.ini."""
        profiles = []
        for browser_dir in self.BROWSER_DIRS:
            directory = Path(browser_dir).expanduser()
            ini = directory / "profiles.ini"
            if not ini.is_file():
                continue
            cp = ConfigParser()
            try:
                cp.read(str(ini))
            except (ConfigParserError, OSError) as e:
                logging.warning(f"Unreadable profiles.ini in {directory}: {e}")
                continue
            for section in cp.sections():
                if not section.startswith("Profile"):
                    continue
                try:
                    raw_path = cp[section]["Path"]
                except KeyError:
                    continue
                # The retired plugin compared IsRelative (a string) to the
                # integer 0, so absolute-path profiles never matched.
                if cp[section].get("IsRelative", "1") == "0":
                    profile = Path(raw_path)
                else:
                    profile = directory / raw_path
                if profile.is_dir():
                    profiles.append(profile)
        return profiles

    def themed_profiles(self, profiles=None):
        """The subset of profiles with firefox-gnome-theme installed."""
        if profiles is None:
            profiles = self.find_profiles()
        return [p for p in profiles
                if (p / "chrome" / self.THEME_DIR_NAME).is_dir()]

    def _hook_path(self, profile):
        return profile / "chrome" / self.THEME_DIR_NAME / "customChrome.css"

    def _is_ours(self, path):
        try:
            with open(path, "r") as f:
                return MARKER in f.read(4096)
        except OSError:
            return False

    def render(self, preset):
        v = dict(preset.variables)
        fg = v.get("window_fg_color", "#ffffff")
        subst = {
            "marker": MARKER,
            "fg_00": _alpha(fg, 0),
            "fg_025": _alpha(fg, 0.025),
            "fg_075": _alpha(fg, 0.075),
            "fg_100": _alpha(fg, 0.100),
            "fg_125": _alpha(fg, 0.125),
            "fg_10": _alpha(fg, 0.1),
            "fg_20": _alpha(fg, 0.2),
            "fg_40": _alpha(fg, 0.4),
            "fg_60": _alpha(fg, 0.6),
            "fg_80": _alpha(fg, 0.8),
            "accent_30": _alpha(v.get("accent_bg_color", "#3584e4"), 0.3),
            "card_60": _alpha(v.get("card_bg_color", "#303030"), 0.6),
            "window_95": _alpha(v.get("window_bg_color", "#242424"), 0.95),
        }
        subst.update(v)
        return TEMPLATE.format(**subst)

    def apply(self, preset):
        """Returns (applied, skipped_foreign, themed_count, profile_count)."""
        css = self.render(preset)
        profiles = self.find_profiles()
        themed = self.themed_profiles(profiles)
        applied, skipped = 0, 0
        for profile in themed:
            hook = self._hook_path(profile)
            if hook.exists() and not self._is_ours(hook):
                logging.warning(
                    f"{hook} exists without our marker — someone else's "
                    "customisations, leaving it alone.")
                skipped += 1
                continue
            try:
                with open(hook, "w") as f:
                    f.write(css)
                applied += 1
                logging.debug(f"Firefox theme written to {hook}")
            except OSError as e:
                logging.error(f"Failed writing {hook}", exc=e)
        return applied, skipped, len(themed), len(profiles)

    def reset(self):
        """Remove our customChrome.css everywhere; never touch foreign ones.
        Returns the number of files removed."""
        removed = 0
        for profile in self.themed_profiles():
            hook = self._hook_path(profile)
            if hook.is_file() and self._is_ours(hook):
                try:
                    hook.unlink()
                    removed += 1
                except OSError as e:
                    logging.error(f"Failed removing {hook}", exc=e)
        return removed
