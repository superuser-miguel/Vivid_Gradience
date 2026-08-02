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

from gradience.frontend.views.firefox_prefs_window import (
    GradienceFirefoxPrefsWindow)

logging = Logger()

THEME_HOMEPAGE = "https://github.com/rafaelmardojai/firefox-gnome-theme"

SKIPPED_KEY = "firefox-skipped-profiles"
KNOWN_KEY = "firefox-known-profiles"


@Gtk.Template(resource_path=f"{rootdir}/ui/firefox_theming_group.ui")
class GradienceFirefoxThemingGroup(Adw.PreferencesGroup):
    __gtype_name__ = "GradienceFirefoxThemingGroup"

    firefox_theming_expander = Gtk.Template.Child("firefox-theming-expander")
    profiles_row = Gtk.Template.Child("profiles-row")
    install_theme_button = Gtk.Template.Child("install-theme-button")
    theme_options_row = Gtk.Template.Child("theme-options-row")
    reset_options_row = Gtk.Template.Child("reset-options-row")
    uninstall_row = Gtk.Template.Child("uninstall-row")

    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        self.app = parent.get_application()
        self.win = self.app.get_active_window()
        self.toast_overlay = parent.toast_overlay
        self.settings = parent.settings

        self.firefox = FirefoxTheme()
        self.installer = FirefoxThemeInstaller()

        self.profile_rows = []
        self.refresh_profiles_row()

    # -- which profiles the engine is allowed to touch ------------------------

    def skipped_keys(self):
        return set(self.settings.get_strv(SKIPPED_KEY))

    def seed_choices(self, profiles):
        """Decide once per profile whether the engine may write to it.

        A profile whose user has picked a Firefox theme of its own is opted
        out on sight — that theme is how they tell one window from another,
        and one preset across every profile would flatten exactly the thing
        profiles are for. Recording the decision separately from the answer
        means turning a profile back on sticks: we never look at it again."""
        known = self.settings.get_strv(KNOWN_KEY)
        skipped = self.settings.get_strv(SKIPPED_KEY)
        unseen = [p for p in profiles if p.key not in known]
        if not unseen:
            return []

        newly_skipped = []
        for profile in unseen:
            known.append(profile.key)
            if self.firefox.has_own_theme(profile):
                skipped.append(profile.key)
                newly_skipped.append(profile)
        self.settings.set_strv(KNOWN_KEY, known)
        if newly_skipped:
            self.settings.set_strv(SKIPPED_KEY, skipped)
        return newly_skipped

    def selected_profiles(self, profiles=None):
        """The profiles the user has left switched on."""
        if profiles is None:
            profiles = self.firefox.find_profiles()
        skipped = self.skipped_keys()
        return [p for p in profiles if p.key not in skipped]

    # -- rows ----------------------------------------------------------------

    def refresh_profiles_row(self, rebuild=True):
        profiles = self.firefox.find_profiles()
        newly_skipped = self.seed_choices(profiles)
        selected = self.selected_profiles(profiles)
        themed = self.firefox.themed_profiles(selected)

        if not profiles:
            subtitle = _("No Firefox profiles found")
        elif len(selected) == len(profiles):
            subtitle = _("{0} profiles, {1} with the Firefox GNOME Theme").format(
                len(profiles), len(themed))
        else:
            subtitle = _("{0} of {1} profiles selected, {2} with the Firefox "
                         "GNOME Theme").format(
                             len(selected), len(profiles), len(themed))
        self.profiles_row.set_subtitle(subtitle)

        # Never while a switch is emitting: rebuilding the list from inside a
        # row's own handler would destroy the widget mid-signal.
        if rebuild:
            self.rebuild_rows(profiles)
        else:
            for row in self.profile_rows:
                row.set_subtitle(self.profile_subtitle(row._profile))

        missing, stale, _foreign = self.installer.plan(selected)
        managed = [p for p in profiles if self.installer.is_managed(p)]

        if missing:
            self.install_theme_button.set_label(_("Install Theme"))
            self.install_theme_button.set_visible(True)
        elif stale:
            self.install_theme_button.set_label(_("Update Theme"))
            self.install_theme_button.set_visible(True)
        else:
            self.install_theme_button.set_visible(False)

        # The options are the theme's own, so they are only reachable once a
        # profile actually has the theme to read them.
        self.theme_options_row.set_sensitive(bool(themed))
        self.theme_options_row.set_subtitle(
            _("Optional features of the Firefox GNOME Theme") if themed
            else _("Install the Firefox GNOME Theme to reach its options"))

        self.uninstall_row.set_visible(bool(managed))
        if managed:
            self.uninstall_row.set_subtitle(
                _("The Firefox GNOME Theme {0} is installed in {1} "
                  "profiles").format(PINNED_TAG, len(managed)))

        if newly_skipped:
            # Switching them off stops the engine writing to them again, but
            # a profile themed before this existed still has our stylesheets
            # in it — so offer to take them back out rather than leaving the
            # switch saying one thing and the profile showing another.
            toast = Adw.Toast(
                title=_("Left {0} alone — a Firefox theme of its own is "
                        "already selected there.").format(
                            ", ".join(p.name for p in newly_skipped)))
            if self.firefox.themed_profiles(newly_skipped):
                toast.set_button_label(_("Remove Colours"))
                toast.connect(
                    "button-clicked",
                    lambda *_a, profiles=newly_skipped:
                        self.remove_colours_from(profiles))
            self.toast_overlay.add_toast(toast)

    def remove_colours_from(self, profiles):
        removed = self.firefox.reset(profiles)
        self.refresh_profiles_row()
        self.toast_overlay.add_toast(Adw.Toast(
            title=_("Removed the generated colours from {0} profiles. "
                    "Restart Firefox to see it go.").format(removed)))

    def rebuild_rows(self, profiles):
        """One switch per profile, rebuilt whole so the order stays: the
        profiles first, then what can be done to them."""
        for row in self.profile_rows:
            self.firefox_theming_expander.remove(row)
        self.profile_rows = []

        for row in (self.theme_options_row, self.reset_options_row,
                    self.uninstall_row):
            if row.get_parent() is not None:
                self.firefox_theming_expander.remove(row)

        skipped = self.skipped_keys()
        for profile in profiles:
            row = Adw.SwitchRow(title=profile.name,
                                subtitle=self.profile_subtitle(profile),
                                active=profile.key not in skipped)
            row._profile = profile
            row.connect("notify::active", self.on_profile_toggled)
            self.firefox_theming_expander.add_row(row)
            self.profile_rows.append(row)

        self.firefox_theming_expander.add_row(self.theme_options_row)
        self.firefox_theming_expander.add_row(self.reset_options_row)
        self.firefox_theming_expander.add_row(self.uninstall_row)

    def profile_subtitle(self, profile):
        own_theme = self.firefox.has_own_theme(profile)
        themed = bool(self.firefox.themed_profiles([profile]))
        if own_theme and themed:
            return _("Has its own Firefox theme; the GNOME Theme will "
                     "override parts of it")
        if own_theme:
            return _("Has its own Firefox theme")
        if themed:
            return _("Firefox GNOME Theme installed")
        return _("No Firefox GNOME Theme yet")

    def on_profile_toggled(self, row, *_args):
        profile = row._profile
        skipped = set(self.settings.get_strv(SKIPPED_KEY))
        if row.get_active():
            skipped.discard(profile.key)
        else:
            skipped.add(profile.key)
            # The switch has to mean the same thing in the profile as it does
            # in the list: off leaves the profile on firefox-gnome-theme's own
            # colours, so whatever the engine wrote there comes back out. The
            # theme itself stays — that is what Uninstall is for.
            if self.firefox.reset([profile]):
                self.toast_overlay.add_toast(Adw.Toast(
                    title=_("Took the preset's colours back out of {0}. "
                            "Restart Firefox to see it go.").format(
                                profile.name)))
        self.settings.set_strv(SKIPPED_KEY, sorted(skipped))
        self.refresh_profiles_row(rebuild=False)

    @Gtk.Template.Callback()
    def on_apply_button_clicked(self, *_args):
        all_profiles = self.firefox.find_profiles()

        if not all_profiles:
            self.refresh_profiles_row()
            self.toast_overlay.add_toast(
                Adw.Toast(title=_("No Firefox profiles found."))
            )
            return

        profiles = self.selected_profiles(all_profiles)
        if not profiles:
            self.toast_overlay.add_toast(
                Adw.Toast(title=_("Every profile is switched off — turn at "
                                  "least one on to theme it."))
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
                       "GNOME Theme, which is not installed in any of the "
                       "profiles you have switched on. Vivid Gradience can "
                       "install a tested release ({0}) into those {1} "
                       "profiles and apply the preset — or install it "
                       "yourself from the project page.").format(
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
                self.app.preset, self.selected_profiles())
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
                      "(their stylesheets were not written by us).").format(
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
        install it into every switched-on profile without the theme, updating
        any of our own installs that fall behind the pin. Runs off the main
        loop; the user's own installs are never touched, and neither are the
        profiles they have switched off."""
        self.install_theme_button.set_sensitive(False)
        self.toast_overlay.add_toast(
            Adw.Toast(title=_("Installing the Firefox GNOME Theme…")))
        selected = self.selected_profiles()

        def worker():
            installed, updated, failed = 0, 0, 0
            try:
                missing, stale, _foreign = self.installer.plan(selected)
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
    def on_theme_options_clicked(self, *_args):
        # Switched-off profiles are left out here too: these options are
        # written into each profile's user.js, and a profile the user has
        # excluded should not have its preferences rewritten either.
        themed = self.firefox.themed_profiles(self.selected_profiles())
        if not themed:
            self.refresh_profiles_row()
            self.toast_overlay.add_toast(
                Adw.Toast(title=_("No switched-on profile has the Firefox "
                                  "GNOME Theme yet."))
            )
            return

        GradienceFirefoxPrefsWindow(
            self, self.installer, themed).present(self.win)

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
        # Every profile, not just the switched-on ones: this is the way back
        # out, and a profile that was themed before it was switched off still
        # has our stylesheets sitting in it.
        removed = self.firefox.reset()
        self.refresh_profiles_row()
        self.toast_overlay.add_toast(
            Adw.Toast(title=_("Removed the generated colours from {0} "
                              "profiles. Restart Firefox to see it "
                              "go.").format(removed))
        )
