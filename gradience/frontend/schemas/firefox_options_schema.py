# firefox_options_schema.py
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

# firefox-gnome-theme's optional features. The theme reads each of these
# through @media -moz-pref(...), so they are plain booleans in user.js and
# every one of them defaults to off — the theme ships only its five required
# prefs. Descriptions follow upstream's README; where upstream warns about a
# feature, so do we, because the switch is ours but the behaviour is not.
#
# Keep this list in step with the pinned tag: a pref the installed release
# does not read is simply inert, but a pref it reads and we omit is a feature
# the user cannot reach from the app.

firefox_options_schema = {
    "groups": [
        {
            "title": _("Tab Bar"),
            "options": [
                {
                    "pref": "gnomeTheme.allTabsButton",
                    "title": _("Show List All Tabs Button"),
                    "subtitle": _("Keep the tab overflow button visible, as "
                                  "stock Firefox does. It is the only way "
                                  "into the tab groups menu."),
                },
                {
                    "pref": "gnomeTheme.allTabsButtonOnOverflow",
                    "title": _("Show List All Tabs Button on Overflow"),
                    "subtitle": _("Show the button only once the tab bar has "
                                  "more tabs than it can fit."),
                },
                {
                    "pref": "gnomeTheme.hideSingleTab",
                    "title": _("Hide Single Tab"),
                    "subtitle": _("Hide the tab bar when only one tab is "
                                  "open. Move the new tab button out of the "
                                  "tab bar first, or it goes with it."),
                },
                {
                    "pref": "gnomeTheme.normalWidthTabs",
                    "title": _("Normal Width Tabs"),
                    "subtitle": _("Use Firefox's default tab width instead "
                                  "of the theme's."),
                },
                {
                    "pref": "gnomeTheme.tabAlignLeft",
                    "title": _("Align Tab Titles Left"),
                    "subtitle": _("Align each tab's title and favicon to the "
                                  "left instead of centring them."),
                },
                {
                    "pref": "gnomeTheme.swapTabClose",
                    "title": _("Swap Tab Close Button Position"),
                    "subtitle": _("Put the tab close buttons on the opposite "
                                  "side from the window controls."),
                },
                {
                    "pref": "gnomeTheme.closeOnlySelectedTabs",
                    "title": _("Close Button on Selected Tab Only"),
                    "subtitle": _("Show the close button on the active tab "
                                  "rather than on every tab."),
                },
                {
                    "pref": "gnomeTheme.activeTabContrast",
                    "title": _("Active Tab Contrast"),
                    "subtitle": _("Give the active tab more contrast against "
                                  "the rest of the tab bar."),
                },
                {
                    "pref": "gnomeTheme.tabsAsHeaderbar",
                    "title": _("Tabs as Headerbar"),
                    "subtitle": _("Move the tabs to the top of the window "
                                  "and let the tab bar hold the window "
                                  "controls, as stock Firefox does."),
                },
            ],
        },
        {
            "title": _("Icons"),
            "options": [
                {
                    "pref": "gnomeTheme.systemIcons",
                    "title": _("Use System Icons"),
                    "subtitle": _("Take icons from your icon theme instead "
                                  "of the Adwaita set the theme bundles. "
                                  "Upstream reports a known colour bug with "
                                  "this on."),
                },
                {
                    "pref": "gnomeTheme.noThemedIcons",
                    "title": _("Keep Firefox Icons"),
                    "subtitle": _("Leave Firefox's own icons alone instead "
                                  "of replacing them."),
                },
                {
                    "pref": "gnomeTheme.symbolicTabIcons",
                    "title": _("Symbolic Tab Icons"),
                    "subtitle": _("Render favicons roughly as symbolic "
                                  "icons."),
                },
            ],
        },
        {
            "title": _("Toolbars"),
            "options": [
                {
                    "pref": "gnomeTheme.bookmarksToolbarUnderTabs",
                    "title": _("Bookmarks Toolbar Under Tabs"),
                    "subtitle": _("Move the bookmarks toolbar below the tab "
                                  "bar."),
                },
                {
                    "pref": "gnomeTheme.bookmarksOnFullscreen",
                    "title": _("Bookmarks Toolbar in Fullscreen"),
                    "subtitle": _("Keep the bookmarks toolbar visible in "
                                  "fullscreen."),
                },
                {
                    "pref": "gnomeTheme.hideUnifiedExtensions",
                    "title": _("Hide Extensions Button"),
                    "subtitle": _("Take the unified extensions button out of "
                                  "the toolbar."),
                },
                {
                    "pref": "gnomeTheme.hideWebrtcIndicator",
                    "title": _("Hide WebRTC Indicator"),
                    "subtitle": _("Hide Firefox's camera and microphone "
                                  "indicator, which GNOME already shows in "
                                  "the top bar."),
                },
                {
                    "pref": "gnomeTheme.dragWindowHeaderbarButtons",
                    "title": _("Drag Window From Headerbar Buttons"),
                    "subtitle": _("Let the window be dragged by its headerbar "
                                  "buttons. Upstream marks this one as "
                                  "buggy: it can fire the button instead."),
                },
            ],
        },
        {
            "title": _("Appearance"),
            "options": [
                {
                    "pref": "gnomeTheme.oledBlack",
                    "title": _("OLED Black"),
                    "subtitle": _("Use the black variant of the dark theme. "
                                  "The preset still supplies the colours "
                                  "around it."),
                },
            ],
        },
        {
            "title": _("Extension Support"),
            "options": [
                {
                    "pref": "gnomeTheme.extensions.adaptiveTabBarColour",
                    "title": _("Adaptive Tab Bar Colour"),
                    "subtitle": _("Style the Adaptive Tab Bar Colour "
                                  "extension. Upstream maintains extension "
                                  "support by community contribution only."),
                },
            ],
        },
    ],
}


def firefox_option_prefs():
    """Every pref the app manages, in schema order."""
    return [option["pref"]
            for group in firefox_options_schema["groups"]
            for option in group["options"]]
