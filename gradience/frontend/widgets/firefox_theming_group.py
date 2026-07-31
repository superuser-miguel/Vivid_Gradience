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

import threading

from subprocess import SubprocessError

from gi.repository import GLib, Gtk, Adw

from gradience.backend.constants import rootdir
from gradience.backend.logger import Logger
from gradience.backend.utils.subprocess import GradienceSubprocess

from gradience.backend.theming.firefox import FirefoxTheme
from gradience.backend.theming.firefox_installer import (
    FirefoxThemeInstaller, PINNED_TAG)

logging = Logger()

THEME_HOMEPAGE = "https://github.com/rafaelmardojai/firefox-gnome-theme"


@Gtk.Template(resource_path=f"{rootdir}/ui/firefox_theming_group.ui")
class GradienceFirefoxThemingGroup(Adw.PreferencesGroup):
    __gtype_name__ = "GradienceFirefoxThemingGroup"

    firefox_theming_expander = Gtk.Template.Child("firefox-theming-expander")
    profiles_row = Gtk.Template.Child("profiles-row")
    install_theme_button = Gtk.Template.Child("install-theme-button")
    reset_options_row = Gtk.Template.Child("reset-options-row")
    uninstall_row = Gtk.Template.Child("uninstall-row")

    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        self.app = parent.get_application()
        self.win = self.app.get_active_window()
        self.toast_overlay = parent.toast_overlay

        self.firefox = FirefoxTheme()
        self.installer = FirefoxThemeInstaller()

        self.firefox_theming_expander.add_row(self.reset_options_row)
        self.firefox_theming_expander.add_row(self.uninstall_row)
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

        missing, stale, _foreign = self.installer.plan(profiles)
        managed = [p for p in profiles if self.installer.is_managed(p)]

        if missing:
            self.install_theme_button.set_label(_("Install Theme"))
            self.install_theme_button.set_visible(True)
        elif stale:
            self.install_theme_button.set_label(_("Update Theme"))
            self.install_theme_button.set_visible(True)
        else:
            self.install_theme_button.set_visible(False)

        self.uninstall_row.set_visible(bool(managed))
        if managed:
            self.uninstall_row.set_subtitle(
                _("The Firefox GNOME Theme {0} is installed in {1} "
                  "profiles").format(PINNED_TAG, len(managed)))

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
            # The one prerequisite the app may install itself: not a system
            # component, just files in profile directories this engine
            # already writes to. A pinned, tested release — never latest.
            dialog = Adw.MessageDialog(
                transient_for=self.win,
                heading=_("Firefox GNOME Theme Missing"),
                body=_("The engine writes its colours through the Firefox "
                       "GNOME Theme, which is not installed in any profile. "
                       "Vivid Gradience can install a tested release ({0}) "
                       "into all {1} profiles and apply the preset — or "
                       "install it yourself from the project page.").format(
                           PINNED_TAG, len(profiles)))

            dialog.add_response("install", _("Install and Apply"))
            dialog.add_response("open-page", _("Open Project Page"))
            dialog.add_response("cancel", _("Cancel"))
            dialog.set_response_appearance(
                "install", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_default_response("install")

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
        if response == "install":
            self.install_theme(apply_after=True)
        elif response == "open-page":
            try:
                GradienceSubprocess().run(
                    ["xdg-open", THEME_HOMEPAGE], allow_escaping=True)
            except (SubprocessError, FileNotFoundError) as e:
                logging.error("Failed to open the theme's project page", exc=e)
                self.toast_overlay.add_toast(
                    Adw.Toast(title=_("Failed to open the project page."))
                )

    @Gtk.Template.Callback()
    def on_install_theme_clicked(self, *_args):
        self.install_theme(apply_after=True)

    def install_theme(self, apply_after=False):
        """Fetch the pinned release (from cache after the first time) and
        install it into every profile without the theme, updating any of our
        own installs that fall behind the pin. Runs off the main loop; the
        user's own installs are never touched."""
        self.install_theme_button.set_sensitive(False)
        self.toast_overlay.add_toast(
            Adw.Toast(title=_("Installing the Firefox GNOME Theme…")))

        def worker():
            installed, updated, failed = 0, 0, 0
            try:
                profiles = self.firefox.find_profiles()
                missing, stale, _foreign = self.installer.plan(profiles)
                tree = self.installer.fetch()
                for profile in missing:
                    try:
                        self.installer.install(profile, tree)
                        installed += 1
                    except OSError as e:
                        logging.error(
                            f"Failed installing into {profile}", exc=e)
                        failed += 1
                for profile in stale:
                    try:
                        self.installer.install(profile, tree)
                        updated += 1
                    except OSError as e:
                        logging.error(f"Failed updating {profile}", exc=e)
                        failed += 1
            except (OSError, GLib.GError) as e:
                logging.error(
                    "Failed to download the Firefox GNOME Theme.", exc=e)
                GLib.idle_add(self.on_install_done, None, None, None,
                              apply_after)
                return
            GLib.idle_add(self.on_install_done, installed, updated, failed,
                          apply_after)

        threading.Thread(target=worker, daemon=True).start()

    def on_install_done(self, installed, updated, failed, apply_after):
        self.install_theme_button.set_sensitive(True)
        self.refresh_profiles_row()

        if installed is None:
            self.toast_overlay.add_toast(
                Adw.Toast(title=_("Failed to download the Firefox GNOME "
                                  "Theme. Check your connection and try "
                                  "again.")))
            return GLib.SOURCE_REMOVE

        if failed:
            self.toast_overlay.add_toast(
                Adw.Toast(title=_("Theme installed into {0} profiles; {1} "
                                  "failed — see the logs.").format(
                                      installed + updated, failed)))
        elif updated and not installed:
            self.toast_overlay.add_toast(
                Adw.Toast(title=_("Theme updated to {0} in {1} "
                                  "profiles.").format(PINNED_TAG, updated)))
        else:
            self.toast_overlay.add_toast(
                Adw.Toast(title=_("Theme {0} installed into {1} "
                                  "profiles.").format(
                                      PINNED_TAG, installed + updated)))

        if apply_after and (installed or updated):
            self.apply_firefox_theme()
        return GLib.SOURCE_REMOVE

    @Gtk.Template.Callback()
    def on_uninstall_theme_clicked(self, *_args):
        managed = [p for p in self.firefox.find_profiles()
                   if self.installer.is_managed(p)]
        dialog = Adw.MessageDialog(
            transient_for=self.win,
            heading=_("Uninstall the Firefox GNOME Theme?"),
            body=_("This removes the theme, its stylesheet imports and its "
                   "preferences from the {0} profiles Vivid Gradience "
                   "installed it into. Copies you installed yourself are "
                   "not touched.").format(len(managed)))
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("uninstall", _("Uninstall"))
        dialog.set_response_appearance(
            "uninstall", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", self.on_uninstall_response)
        dialog.present()

    def on_uninstall_response(self, _widget, response, *_args):
        if response != "uninstall":
            return
        removed = 0
        for profile in self.firefox.find_profiles():
            try:
                if self.installer.uninstall(profile):
                    removed += 1
            except OSError as e:
                logging.error(f"Failed uninstalling from {profile}", exc=e)
        self.refresh_profiles_row()
        self.toast_overlay.add_toast(
            Adw.Toast(title=_("Uninstalled the theme from {0} profiles. "
                              "Restart Firefox to see it go.").format(removed))
        )

    @Gtk.Template.Callback()
    def on_reset_theme_clicked(self, *_args):
        removed = self.firefox.reset()
        self.refresh_profiles_row()
        self.toast_overlay.add_toast(
            Adw.Toast(title=_("Removed the generated colours from {0} "
                              "profiles.").format(removed))
        )
