# custom_themes_group.py
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

from gi.repository import GLib, Gtk, Adw

from gradience.backend.constants import rootdir
from gradience.backend.logger import Logger

from gradience.backend.theming import custom_themes

logging = Logger()


@Gtk.Template(resource_path=f"{rootdir}/ui/custom_themes_group.ui")
class GradienceCustomThemesGroup(Adw.PreferencesGroup):
    __gtype_name__ = "GradienceCustomThemesGroup"

    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        self.win = parent
        self.toast_overlay = parent.toast_overlay

        self.rows = []
        self.refresh()

    def refresh(self, *_args):
        for row in self.rows:
            self.remove(row)
        self.rows = []

        themes = custom_themes.list_themes()
        if not themes:
            row = Adw.ActionRow(
                title=_("No custom themes yet"),
                subtitle=_("Import one, or let Apply rescue an existing stylesheet"))
            row.set_sensitive(False)
            self.add(row)
            self.rows.append(row)
            return

        for theme in themes:
            provides = ", ".join(theme["provides"]) or _("no toolkit directories")
            row = Adw.ActionRow(title=theme["name"], subtitle=provides)

            remove = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER,
                                tooltip_text=_("Remove this theme"))
            remove.add_css_class("flat")
            remove.connect("clicked", self.on_remove_clicked, theme["name"])
            row.add_suffix(remove)

            self.add(row)
            self.rows.append(row)

    @Gtk.Template.Callback()
    def on_import_button_clicked(self, *_args):
        dialog = Gtk.FileDialog(title=_("Choose a Theme Folder"), modal=True)
        dialog.select_folder(self.win, None, self._on_folder_chosen)

    def _on_folder_chosen(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:  # dismissed
            return
        if folder is None:
            return

        try:
            name = custom_themes.import_theme(folder.get_path())
        except (OSError, NotADirectoryError) as e:
            logging.error("Failed to import the theme folder.", exc=e)
            self.toast_overlay.add_toast(
                Adw.Toast(title=_("Failed to import the theme folder.")))
            return

        self.refresh()
        self.toast_overlay.add_toast(
            Adw.Toast(title=_("Imported as {0}.").format(name)))

    def on_remove_clicked(self, _button, name):
        dialog = Adw.MessageDialog(
            transient_for=self.win,
            heading=_("Remove {0}?").format(name),
            body=_("The theme's files are deleted from ~/.local/share/themes. "
                   "This cannot be undone."))
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("remove", _("Remove"))
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", self._on_remove_response, name)
        dialog.present()

    def _on_remove_response(self, _dialog, response, name):
        if response != "remove":
            return
        try:
            custom_themes.remove_theme(name)
        except (OSError, ValueError) as e:
            logging.error(f"Failed to remove theme {name!r}.", exc=e)
            self.toast_overlay.add_toast(
                Adw.Toast(title=_("Failed to remove the theme.")))
            return
        self.refresh()
        self.toast_overlay.add_toast(
            Adw.Toast(title=_("Removed {0}.").format(name)))
