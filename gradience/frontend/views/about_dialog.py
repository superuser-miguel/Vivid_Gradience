# about_dialog.py
#
# Change the look of Adwaita, with ease
# Copyright (C) 2025, Gradience Team
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

from gradience.backend import constants


# TRANSLATORS: This is a place to put your credits (formats:
# "Name https://example.com" or "Name <email@example.com>",
# no quotes) and is not meant to be translated literally.
translator_credits = _("translator-credits")

class GradienceAboutDialog:
    def __init__(self, parent):
        self.parent = parent
        self.app = self.parent.get_application()

        self.setup()

def setup(self):
        self.about_dialog = Adw.AboutDialog(
            application_name="Vivid Gradience",
            application_icon=constants.app_id,
            developer_name=_("superuser-miguel"),
            website=constants.project_url,
            support_url=constants.help_url,
            issue_url=constants.bugtracker_url,
            developers=[
                "superuser-miguel https://github.com/superuser-miguel",
            ],
            designers=[
                "David Lapshin https://github.com/daudix-UFO"
            ],
            translator_credits=_(translator_credits),
            copyright=_("Copyright © 2022-2025 superuser-miguel"),
            license_type=Gtk.License.GPL_3_0,
            version=constants.version,
            release_notes_version=constants.rel_ver,
        )

        self.about_dialog.add_credit_section(
            _("Original Gradience Team"),
            [
                "Artyom Fomin https://github.com/ArtyIF",
                "0xMRTT https://github.com/0xMRTT",
                "Verantor https://github.com/Verantor",
                "tfuxu https://github.com/tfuxu",
                "u1F98E https://github.com/u1f98e",
                "David Lapshin https://github.com/daudix-UFO"
            ]
        )

    def show_about(self):
        self.about_dialog.present(self.parent)
