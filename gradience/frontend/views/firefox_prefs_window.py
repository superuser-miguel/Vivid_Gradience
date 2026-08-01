# firefox_prefs_window.py
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

from gi.repository import Gtk, Adw

from gradience.backend.constants import rootdir
from gradience.backend.logger import Logger

from gradience.frontend.schemas.firefox_options_schema import (
    firefox_options_schema, firefox_option_prefs)

logging = Logger()


@Gtk.Template(resource_path=f"{rootdir}/ui/firefox_prefs_window.ui")
class GradienceFirefoxPrefsWindow(Adw.PreferencesDialog):
    """The theme's own optional features, as switches.

    The theme ships these off and reads them straight out of user.js, so the
    profiles are the state — there is nothing to keep in sync in GSettings,
    and a pref the user set by hand shows up here as the switch it is."""

    __gtype_name__ = "GradienceFirefoxPrefsWindow"

    options_page = Gtk.Template.Child("options-page")

    def __init__(self, parent, installer, profiles, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        self.installer = installer
        self.profiles = profiles

        self.prefs = firefox_option_prefs()
        self.switches = {}
        self.loading = True

        self.setup()
        self.loading = False

    def current_options(self):
        """A pref counts as on only when every themed profile has it on, so a
        switch never reads on while some profile quietly disagrees. Writing
        settles the disagreement, since a write goes to all of them."""
        per_profile = [self.installer.read_options(profile, self.prefs)
                       for profile in self.profiles]
        return {pref: all(values[pref] for values in per_profile)
                for pref in self.prefs}

    def setup(self):
        values = self.current_options()

        for group in firefox_options_schema["groups"]:
            pref_group = Adw.PreferencesGroup(title=group["title"])
            for option in group["options"]:
                row = Adw.SwitchRow(
                    title=option["title"],
                    subtitle=option["subtitle"],
                    active=values[option["pref"]],
                )
                row.connect("notify::active", self.on_option_toggled)
                self.switches[option["pref"]] = row
                pref_group.add(row)
            self.options_page.add(pref_group)

    def on_option_toggled(self, *_args):
        if self.loading:
            return

        options = {pref: row.get_active()
                   for pref, row in self.switches.items()}
        failed = 0
        for profile in self.profiles:
            try:
                self.installer.write_options(profile, options)
            except OSError as e:
                logging.error(f"Failed writing theme options to {profile}",
                              exc=e)
                failed += 1

        if failed:
            self.parent.toast_overlay.add_toast(
                Adw.Toast(title=_("Could not write the theme options to {0} "
                                  "profiles — see the logs.").format(failed))
            )
