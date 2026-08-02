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

# firefox-gnome-theme designates two hooks for user overrides, one per
# stylesheet origin: customChrome.css is imported from userChrome.css (chrome
# documents) and customContent.css from userContent.css (content documents,
# which is where every about: page lives). Both are the user's files, not the
# theme's, and may hold their own CSS. The marker fences our claim — a hook
# without it is someone else's work and is never overwritten (see the
# stylesheet-ownership principles).
MARKER = "Generated with Vivid Gradience"

# The palette both origins need.
#
# It has to be restated on the content side rather than inherited: the theme
# imports its own colors/light.css and colors/dark.css from *both* entry
# stylesheets, so a content document that only ever saw customChrome.css was
# reading the theme's stock #222226 no matter which preset was loaded.
#
# Only variables the pinned release actually reads. The theme drops and
# renames these between versions, and one it no longer reads is a colour the
# preset silently stops reaching — so when the pin moves, check this list
# against the release rather than assuming it still lands.
PALETTE = """:root {{
    --gnome-window-background:                     {window_bg_color};
    --gnome-window-color:                          {window_fg_color};
    --gnome-view-background:                       {view_bg_color};
    --gnome-sidebar-background:                    {sidebar_bg_color};
    --gnome-secondary-sidebar-background:          {sidebar_bg_color};
    --gnome-card-background:                       {card_bg_color};
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
"""

CHROME_TEMPLATE = """/* {marker}
 *
 * Written by the Firefox engine from the preset's colours, for Firefox's
 * chrome windows. Reapplying a preset rewrites this file; delete it (or
 * Remove Colours in the app) to fall back to firefox-gnome-theme's own.
 * Requires https://github.com/rafaelmardojai/firefox-gnome-theme in this
 * profile. Its companion is customContent.css, which covers about: pages.
 */

""" + PALETTE + """
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

/* The Library (Bookmarks, History) and the profile windows.
 *
 * Neither Firefox nor firefox-gnome-theme paints these from a theme colour.
 * The Library takes system colours — organizer.css sets `background-color:
 * Window` on its root view, and several of its widgets are drawn natively
 * through `appearance: auto`. The profile pages resolve their design tokens
 * to Canvas, Field and AccentColor on Linux. So both ask GTK, and libadwaita
 * answers with stock Adwaita no matter which preset is loaded — the same
 * constraint this whole app exists to work around. They were never ignoring
 * the theme; the colour simply had no route in.
 *
 * A declaration outranks a system-colour default, so naming the surfaces is
 * enough. The Library's ids belong to places.xhtml alone and need no
 * scoping; the profile pages are keyed by URL because their token names are
 * global. Most other in-content tokens are color-mix() over currentColor, so
 * setting the canvas and the text colour carries buttons, borders and hover
 * states along with it. These live here rather than in customContent.css
 * because they are chrome windows in their own right, not content: the
 * Library is places.xhtml and the profile pages open through
 * toOpenWindowByType with chrome flags. */

#placesView,
#detailsPane {{
    background-color: {window_bg_color} !important;
    color: {window_fg_color} !important;
}}
#placesToolbar {{
    background-color: {headerbar_bg_color} !important;
    color: {headerbar_fg_color} !important;
}}
#placesList {{
    background-color: {sidebar_bg_color} !important;
    color: {sidebar_fg_color} !important;
}}
#contentView,
#placesContent {{
    background-color: {view_bg_color} !important;
    color: {view_fg_color} !important;
}}
treechildren::-moz-tree-row {{
    background-color: transparent !important;
}}
treechildren::-moz-tree-cell-text {{
    color: {view_fg_color} !important;
}}
treechildren::-moz-tree-row(selected) {{
    background-color: {accent_bg_color} !important;
}}
treechildren::-moz-tree-cell-text(selected) {{
    color: {accent_fg_color} !important;
}}

@-moz-document url("about:profilemanager"), url("about:newprofile"),
               url("about:editprofile"), url("about:deleteprofile"),
               url("chrome://global/content/print.html") {{
{in_content_tokens}
    body {{
        background-color: {window_bg_color} !important;
        color: {window_fg_color} !important;
    }}
}}
"""

# Firefox's own in-content design tokens, from tokens-platform.css. On Linux
# most of them resolve to a GTK system colour (Canvas, Field, AccentColor,
# LinkText, -moz-sidebar, -moz-headerbar), which is why Settings, Add-ons and
# the print dialog stayed stock Firefox next to a themed chrome. The rest of
# the token set is color-mix() over currentColor, so naming the canvas, the
# text colour and the accent carries buttons, borders and hover states along.
IN_CONTENT_TOKENS = """    :root {{
        color: {window_fg_color} !important;
        --text-color: {window_fg_color} !important;
        --background-color-canvas: {window_bg_color} !important;
        --panel-background-color: {popover_bg_color} !important;
        --panel-text-color: {popover_fg_color} !important;
        --input-text-background-color: {view_bg_color} !important;
        --input-text-color: {view_fg_color} !important;
        --color-accent-primary: {accent_bg_color} !important;
        --color-accent-attention: {accent_bg_color} !important;
        --color-accent-primary-selected: {accent_bg_color} !important;
        --button-text-color-primary: {accent_fg_color} !important;
        --text-color-accent-primary-selected: {accent_fg_color} !important;
        --table-header-text-color: {accent_fg_color} !important;
        --toolbarbutton-icon-fill-attention: {accent_bg_color} !important;
        --link-color: {accent_color} !important;
        --sidebar-background-color: {sidebar_bg_color} !important;
        --sidebar-text-color: {sidebar_fg_color} !important;
        --toolbox-background-color: {headerbar_bg_color} !important;
        --toolbox-text-color: {headerbar_fg_color} !important;
        --toolbar-text-color: {window_fg_color} !important;
    }}"""

# The about: pages worth claiming. Listed rather than globbed on purpose:
# these token names are generic, and a bare :root rule in a *content* sheet
# would repaint every web page you visit, not just Firefox's own.
IN_CONTENT_PAGES = ", ".join(
    f"url-prefix(about:{page})" for page in (
        "preferences", "addons", "logins", "loginsimportreport",
        "protections", "downloads", "certificate", "profiles", "config",
        "support", "sessionrestore", "policies", "processes", "translations",
        "webauthn",
    ))

CONTENT_TEMPLATE = """/* {marker}
 *
 * Written by the Firefox engine from the preset's colours, for Firefox's
 * content documents — every about: page, including the new tab and Settings.
 * Reapplying a preset rewrites this file; delete it (or Remove Colours in
 * the app) to fall back to firefox-gnome-theme's own colours. Requires
 * https://github.com/rafaelmardojai/firefox-gnome-theme in this profile.
 * Its companion is customChrome.css, which covers the browser windows.
 */

""" + PALETTE + """
/* about:home and about:newtab, from the same preset roles as everything
 * else. This block used to live in customChrome.css, where it could never
 * have worked: userChrome.css is a sheet for *chrome* documents and the new
 * tab is content. The theme's own newtab rules are in userContent.css for
 * exactly this reason. */
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

/* Firefox's own in-content pages. Scoped per URL rather than set at :root
 * because this is a content sheet: an unscoped rule here would repaint every
 * website you visit. */
@-moz-document {in_content_pages} {{
{in_content_tokens}
    body {{
        background-color: {window_bg_color} !important;
        color: {window_fg_color} !important;
    }}
}}
"""

# Spliced in rather than passed to format(): the token block carries its own
# doubled braces, so it has to be part of the template before the single
# format() pass, not a value handed to it.
CHROME_TEMPLATE = CHROME_TEMPLATE.replace(
    "{in_content_tokens}", IN_CONTENT_TOKENS)
CONTENT_TEMPLATE = CONTENT_TEMPLATE.replace(
    "{in_content_tokens}", IN_CONTENT_TOKENS).replace(
    "{in_content_pages}", IN_CONTENT_PAGES)


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


class FirefoxProfile:
    """One Firefox profile, as the app needs to talk about it: a path, the
    name the user gave it, and which browser it belongs to."""

    def __init__(self, path, name, browser):
        self.path = Path(path)
        self.name = name
        self.browser = browser

    @property
    def key(self):
        """Stable identity for the opt-out list. The directory path is what
        profiles.ini keys on and what survives a rename in the profile
        manager, which the display name does not."""
        return str(self.path)

    def __fspath__(self):
        return str(self.path)

    def __truediv__(self, other):
        return self.path / other

    def __eq__(self, other):
        return self.key == getattr(other, "key", None)

    def __hash__(self):
        return hash(self.key)

    def __str__(self):
        return str(self.path)

    def __repr__(self):
        return f"<FirefoxProfile {self.name} at {self.path}>"


class FirefoxTheme:
    """Write the current preset into firefox-gnome-theme's customChrome.css
    and customContent.css hooks, per profile, for every browser the Flatpak
    is granted."""

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

    # Firefox ships four themes of its own. Three of them only choose between
    # light and dark and carry no colour, so they are no obstacle to a preset.
    # Alpenglow is a real colour scheme and counts as the user's choice, the
    # same as any theme from addons.mozilla.org.
    NEUTRAL_THEME_IDS = {
        "default-theme@mozilla.org",
        "firefox-compact-light@mozilla.org",
        "firefox-compact-dark@mozilla.org",
    }

    THEME_ID_RE = re.compile(
        r'user_pref\(\s*"extensions\.activeThemeID"\s*,\s*"([^"]*)"\s*\)')

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
                    path = Path(raw_path)
                else:
                    path = directory / raw_path
                if path.is_dir():
                    profiles.append(FirefoxProfile(
                        path,
                        cp[section].get("Name", path.name),
                        directory.name.lstrip(".")))
        return profiles

    def themed_profiles(self, profiles=None):
        """The subset of profiles with firefox-gnome-theme installed."""
        if profiles is None:
            profiles = self.find_profiles()
        return [p for p in profiles
                if (p / "chrome" / self.THEME_DIR_NAME).is_dir()]

    # -- the user's own choices ----------------------------------------------

    def active_theme_id(self, profile):
        """The add-on theme this profile has selected, or None if it has never
        been started. Read from prefs.js rather than the extensions database
        because it is a plain text file we can parse without a JSON schema we
        do not control."""
        try:
            content = (Path(profile) / "prefs.js").read_text()
        except OSError:
            return None
        matches = self.THEME_ID_RE.findall(content)
        return matches[-1] if matches else None

    def has_own_theme(self, profile):
        """Whether the user has deliberately given this profile a colour of
        its own. Profiles are a way to keep work apart, and people theme them
        so they can tell one window from another at a glance — so a preset
        should not walk over that without being asked."""
        theme_id = self.active_theme_id(profile)
        return bool(theme_id) and theme_id not in self.NEUTRAL_THEME_IDS

    # -- hooks ---------------------------------------------------------------

    def _hook_paths(self, profile):
        """Both of the theme's user-override hooks, chrome first."""
        base = Path(profile) / "chrome" / self.THEME_DIR_NAME
        return base / "customChrome.css", base / "customContent.css"

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
        # Sidebar roles arrived in libadwaita 1.4, so a preset imported from
        # an older Gradience may not carry them. Falling back keeps the whole
        # stylesheet from failing over one absent colour.
        for role, fallback in (("sidebar_bg_color", "window_bg_color"),
                               ("sidebar_fg_color", "window_fg_color"),
                               ("headerbar_fg_color", "window_fg_color"),
                               ("popover_fg_color", "window_fg_color"),
                               ("accent_fg_color", "window_bg_color")):
            if not subst.get(role):
                subst[role] = subst.get(fallback, "#ffffff")
        return (CHROME_TEMPLATE.format(**subst),
                CONTENT_TEMPLATE.format(**subst))

    def apply(self, preset, profiles=None):
        """Write both hooks into `profiles` — the caller's choice, not every
        profile on the machine, because a profile the user has themed by hand
        is theirs.

        Returns (applied, skipped_foreign, themed_count, profile_count)."""
        chrome_css, content_css = self.render(preset)
        all_profiles = self.find_profiles()
        if profiles is None:
            profiles = all_profiles
        themed = self.themed_profiles(profiles)
        applied, skipped = 0, 0
        for profile in themed:
            hooks = self._hook_paths(profile)
            foreign = [h for h in hooks if h.exists() and not self._is_ours(h)]
            if foreign:
                logging.warning(
                    f"{', '.join(str(h) for h in foreign)} exists without our "
                    "marker — someone else's customisations, leaving the "
                    "profile alone.")
                skipped += 1
                continue
            wrote = False
            for hook, css in zip(hooks, (chrome_css, content_css)):
                try:
                    with open(hook, "w") as f:
                        f.write(css)
                    wrote = True
                    logging.debug(f"Firefox theme written to {hook}")
                except OSError as e:
                    logging.error(f"Failed writing {hook}", exc=e)
            applied += bool(wrote)
        return applied, skipped, len(themed), len(all_profiles)

    def reset(self, profiles=None):
        """Remove both of our hooks; never touch files that are not ours.
        Returns the number of profiles cleared."""
        if profiles is None:
            profiles = self.find_profiles()
        cleared = 0
        for profile in self.themed_profiles(profiles):
            removed = False
            for hook in self._hook_paths(profile):
                if hook.is_file() and self._is_ours(hook):
                    try:
                        hook.unlink()
                        removed = True
                    except OSError as e:
                        logging.error(f"Failed removing {hook}", exc=e)
            cleared += removed
        return cleared
