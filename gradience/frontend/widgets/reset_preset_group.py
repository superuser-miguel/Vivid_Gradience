# reset_preset_group.py
#
# Change the look of Adwaita, with ease
# Copyright (C) 2023, Gradience Team
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

from gi.repository import GLib, Gtk, Adw

from gradience.backend.constants import rootdir
from gradience.backend.logger import Logger
from gradience.backend.theming.preset import PresetUtils
from gradience.backend.theming.backup import ThemeBackup

logging = Logger()


@Gtk.Template(resource_path=f"{rootdir}/ui/reset_preset_group.ui")
class GradienceResetPresetGroup(Adw.PreferencesGroup):
    __gtype_name__ = "GradienceResetPresetGroup"

    original_libadw_row = Gtk.Template.Child()
    original_gtk3_row = Gtk.Template.Child()

    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent

        self.app = self.parent.get_application()
        self.win = self.parent

        self.setup_signals()
        self.setup()

    def setup_signals(self):
        pass

    def setup(self):
        self.refresh_original_rows()

    def refresh_original_rows(self):
        """Show an original-theme row only when we actually hold a backup."""
        for app_type, row in (
            ("gtk4", self.original_libadw_row),
            ("gtk3", self.original_gtk3_row),
        ):
            backup = ThemeBackup(app_type)

            if not backup.has_original():
                row.set_visible(False)
                continue

            if backup.original_meta().get("kind") == "foreign":
                subtitle = _("A theme that was already installed, saved before it was replaced")
            else:
                subtitle = _("The stylesheet in place before Vivid Gradience first applied a preset")

            row.set_subtitle(subtitle)
            row.set_visible(True)

    def _restore_original(self, app_type: str, label: str):
        try:
            ThemeBackup(app_type).restore("original")
        except (OSError, FileNotFoundError) as e:
            logging.error(f"Unable to restore original {app_type} theme.", exc=e)
            self.parent.add_toast(
                Adw.Toast(title=_("Unable to restore the original {} theme").format(label))
            )
        else:
            self.parent.add_toast(
                Adw.Toast(
                    title=_("Original {} theme has been restored. Log out to apply changes.").format(label)
                )
            )
            self.refresh_original_rows()

    @Gtk.Template.Callback()
    def on_libadw_restore_original_clicked(self, *_args):
        self._restore_original("gtk4", "GTK 4")

    @Gtk.Template.Callback()
    def on_gtk3_restore_original_clicked(self, *_args):
        self._restore_original("gtk3", "GTK 3")

    @Gtk.Template.Callback()
    def on_libadw_restore_button_clicked(self, *_args):
        try:
            PresetUtils().restore_preset("gtk4")
        except (OSError, GLib.GError):
            self.parent.add_toast(
                Adw.Toast(title=_("Unable to restore GTK 4 backup"))
            )
        else:
            toast = Adw.Toast(
                title=_("GTK 4 preset has been restored. Log out to apply changes."),
            )
            self.parent.add_toast(toast)

    @Gtk.Template.Callback()
    def on_libadw_reset_button_clicked(self, *_args):
        try:
            PresetUtils().reset_preset("gtk4")
        except GLib.GError:
            self.parent.add_toast(
                Adw.Toast(title=_("Unable to delete current preset"))
            )
        else:
            toast = Adw.Toast(
                title=_("GTK 4 theme has been reset. Log out to apply changes."),
            )
            self.parent.add_toast(toast)


    @Gtk.Template.Callback()
    def on_gtk3_restore_button_clicked(self, *_args):
        try:
            PresetUtils().restore_preset("gtk3")
        except (OSError, GLib.GError):
            self.parent.add_toast(
                Adw.Toast(title=_("Unable to restore GTK 3 backup"))
            )
        else:
            toast = Adw.Toast(
                title=_("GTK 3 preset has been restored. Log out to apply changes."),
            )
            self.parent.add_toast(toast)

    @Gtk.Template.Callback()
    def on_gtk3_reset_button_clicked(self, *_args):
        try:
            PresetUtils().reset_preset("gtk3")
        except GLib.GError:
            self.parent.add_toast(
                Adw.Toast(title=_("Unable to delete current preset"))
            )
        else:
            toast = Adw.Toast(
                title=_("GTK 3 theme has been reset. Log out to apply changes."),
            )
            self.parent.add_toast(toast)
