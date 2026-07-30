# icon_theming_group.py
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

from gradience.backend.theming.icons import IconTheme

logging = Logger()


@Gtk.Template(resource_path=f"{rootdir}/ui/icon_theming_group.ui")
class GradienceIconThemingGroup(Adw.PreferencesGroup):
    __gtype_name__ = "GradienceIconThemingGroup"

    icon_theming_expander = Gtk.Template.Child("icon-theming-expander")
    ramp_row = Gtk.Template.Child("ramp-row")
    reset_options_row = Gtk.Template.Child("reset-options-row")

    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        self.app = parent.get_application()
        self.win = self.app.get_active_window()
        self.toast_overlay = parent.toast_overlay

        self.icon_theming_expander.add_row(self.reset_options_row)

        self.app.connect("preset-reload", self.refresh_ramp_row)
        self.refresh_ramp_row()

    def _icon_theme(self):
        return IconTheme()

    def refresh_ramp_row(self, *_args):
        try:
            chosen = self._icon_theme().choice(self.app.preset)
        except (GLib.GError, SubprocessError, AttributeError, ValueError) as e:
            logging.warning(f"Could not score icon ramps: {e}")
            chosen = None

        if chosen is None:
            self.ramp_row.set_subtitle(_("Scored when a preset is loaded"))
            return

        self.ramp_row.set_subtitle(
            _("{0} — {1} (contrast {2} against the view)").format(
                "@" + chosen["ramp"], chosen["why"],
                f"{chosen['contrast']:.2f}"))

    @Gtk.Template.Callback()
    def on_apply_button_clicked(self, *_args):
        try:
            chosen, n_colours, n_files = self._icon_theme().apply(self.app.preset)
        except (OSError, ValueError, GLib.GError, SubprocessError) as e:
            logging.error(
                "An error occurred while generating the icon theme.", exc=e)
            self.toast_overlay.add_toast(
                Adw.Toast(title=_(
                    "An error occurred while generating the icon theme."))
            )
            return

        self.refresh_ramp_row()
        self.toast_overlay.add_toast(
            Adw.Toast(title=_(
                "Icon theme applied: {0} icons recoloured through {1}.").format(
                    n_files, "@" + chosen["ramp"]))
        )

    @Gtk.Template.Callback()
    def on_reset_theme_clicked(self, *_args):
        try:
            removed = self._icon_theme().remove()
        except (OSError, GLib.GError, SubprocessError) as e:
            logging.error(
                "An error occurred while removing the icon theme.", exc=e)
            self.toast_overlay.add_toast(
                Adw.Toast(title=_(
                    "An error occurred while removing the icon theme."))
            )
            return

        if removed:
            title = _("Icon theme removed; the default is selected again.")
        else:
            title = _("No generated icon theme to remove.")
        self.toast_overlay.add_toast(Adw.Toast(title=title))
