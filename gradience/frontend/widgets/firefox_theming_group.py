# firefox_theming_group.py
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

from subprocess import SubprocessError

from gi.repository import GLib, Gtk, Adw

from gradience.backend.constants import rootdir
from gradience.backend.logger import Logger
from gradience.backend.utils.subprocess import GradienceSubprocess

from gradience.backend.theming.firefox import FirefoxTheme

logging = Logger()

THEME_HOMEPAGE = "https://github.com/rafaelmardojai/firefox-gnome-theme"


@Gtk.Template(resource_path=f"{rootdir}/ui/firefox_theming_group.ui")
class GradienceFirefoxThemingGroup(Adw.PreferencesGroup):
    __gtype_name__ = "GradienceFirefoxThemingGroup"

    firefox_theming_expander = Gtk.Template.Child("firefox-theming-expander")
    profiles_row = Gtk.Template.Child("profiles-row")
    reset_options_row = Gtk.Template.Child("reset-options-row")

    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        self.app = parent.get_application()
        self.win = self.app.get_active_window()
        self.toast_overlay = parent.toast_overlay

        self.firefox = FirefoxTheme()

        self.firefox_theming_expander.add_row(self.reset_options_row)
        self.refresh_profiles_row()

    def refresh_profiles_row(self):
        profiles = self.firefox.find_profiles()
        themed = self.firefox.themed_profiles(profiles)
        if not profiles:
            subtitle = _("No Firefox profiles found")
        else:
            subtitle = _("{0} profiles, {1} with the Firefox GNOME Theme").format(
                len(profiles), len(themed))
        self.profiles_row.set_subtitle(subtitle)

    @Gtk.Template.Callback()
    def on_apply_button_clicked(self, *_args):
        profiles = self.firefox.find_profiles()

        if not profiles:
            self.refresh_profiles_row()
            self.toast_overlay.add_toast(
                Adw.Toast(title=_("No Firefox profiles found."))
            )
            return

        if not self.firefox.themed_profiles(profiles):
            # Same decision as the Shell engine's missing-extension dialog:
            # say what is missing and where it comes from, install nothing.
            dialog = Adw.MessageDialog(
                transient_for=self.win,
                heading=_("Firefox GNOME Theme Missing"),
                body=_("The engine writes its colours through the Firefox "
                       "GNOME Theme, which is not installed in any profile. "
                       "Install it from its project page, then apply again."))

            dialog.add_response("open-page", _("Open Project Page"))
            dialog.add_response("cancel", _("Cancel"))
            dialog.set_response_appearance(
                "open-page", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_default_response("open-page")

            dialog.connect("response", self.on_theme_missing_response)
            dialog.present()
            return

        self.apply_firefox_theme()

    def apply_firefox_theme(self):
        try:
            applied, skipped, _themed, _total = self.firefox.apply(
                self.app.preset)
        except (OSError, GLib.GError, KeyError) as e:
            logging.error(
                "An error occurred while generating the Firefox theme.", exc=e)
            self.toast_overlay.add_toast(
                Adw.Toast(title=_(
                    "An error occurred while generating the Firefox theme."))
            )
            return

        self.refresh_profiles_row()

        if skipped:
            title = _("Firefox theme applied to {0} profiles; {1} skipped "
                      "(customChrome.css not written by us).").format(
                          applied, skipped)
        else:
            title = _("Firefox theme applied to {0} profiles. "
                      "Restart Firefox to see it.").format(applied)
        self.toast_overlay.add_toast(Adw.Toast(title=title))

    def on_theme_missing_response(self, _widget, response, *_args):
        if response == "open-page":
            try:
                GradienceSubprocess().run(
                    ["xdg-open", THEME_HOMEPAGE], allow_escaping=True)
            except (SubprocessError, FileNotFoundError) as e:
                logging.error("Failed to open the theme's project page", exc=e)
                self.toast_overlay.add_toast(
                    Adw.Toast(title=_("Failed to open the project page."))
                )

    @Gtk.Template.Callback()
    def on_reset_theme_clicked(self, *_args):
        removed = self.firefox.reset()
        self.refresh_profiles_row()
        self.toast_overlay.add_toast(
            Adw.Toast(title=_("Removed the generated theme from {0} "
                              "profiles.").format(removed))
        )
