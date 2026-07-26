# monet_theming_group.py
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

from gi.repository import Gtk, Adw

from gradience.backend.theming.monet import Monet, SCHEME_VARIANTS, CONTRAST_LEVELS
from gradience.backend.constants import rootdir

from gradience.frontend.widgets.palette_shades import GradiencePaletteShades

from gradience.backend.logger import Logger

logging = Logger()


@Gtk.Template(resource_path=f"{rootdir}/ui/monet_theming_group.ui")
class GradienceMonetThemingGroup(Adw.PreferencesGroup):
    __gtype_name__ = "GradienceMonetThemingGroup"

    monet_theming_expander = Gtk.Template.Child("monet-theming-expander")
    monet_file_chooser = Gtk.Template.Child("monet-file-chooser")
    monet_file_chooser_button = Gtk.Template.Child("file-chooser-button")

    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        self.app = self.parent.get_application()

        self.monet_image_file = None

        self.setup()

    def setup(self):
        self.setup_palette_shades()
        self.setup_variant_row()
        self.setup_contrast_row()
        self.setup_theme_row()

        # Re-apply live when any option changes — but only once a wallpaper has
        # been picked, so tweaking a combo before that stays a no-op.
        for row in (self.variant_row, self.contrast_row, self.theme_row):
            row.connect("notify::selected", self._on_option_changed)

    def setup_palette_shades(self):
        self.monet_palette_shades = GradiencePaletteShades(
            "monet", _("Palette"), 6
        )
        self.app.pref_palette_shades["monet"] = self.monet_palette_shades

        self.monet_theming_expander.add_row(self.monet_palette_shades)

    def setup_variant_row(self):
        self.variant_row = Adw.ComboRow()
        self.variant_row.set_title(_("Style"))
        self.variant_row.set_subtitle(_("Material You scheme variant"))

        labels = {
            "vibrant": _("Vibrant"),
            "tonal_spot": _("Tonal Spot"),
            "expressive": _("Expressive"),
            "fidelity": _("Fidelity"),
            "content": _("Content"),
            "neutral": _("Neutral"),
            "monochrome": _("Monochrome"),
            "rainbow": _("Rainbow"),
            "fruit_salad": _("Fruit Salad"),
        }
        self._variant_keys = list(SCHEME_VARIANTS.keys())

        store = Gtk.StringList()
        for key in self._variant_keys:
            store.append(labels.get(key, key))
        self.variant_row.set_model(store)
        self.variant_row.set_selected(0)  # DEFAULT_VARIANT is the first entry

        self.monet_theming_expander.add_row(self.variant_row)

    def setup_contrast_row(self):
        self.contrast_row = Adw.ComboRow()
        self.contrast_row.set_title(_("Contrast"))

        labels = {
            "standard": _("Standard"),
            "medium": _("Medium"),
            "high": _("High"),
        }
        self._contrast_keys = list(CONTRAST_LEVELS.keys())

        store = Gtk.StringList()
        for key in self._contrast_keys:
            store.append(labels.get(key, key))
        self.contrast_row.set_model(store)
        self.contrast_row.set_selected(0)

        self.monet_theming_expander.add_row(self.contrast_row)

    def setup_theme_row(self):
        self.theme_row = Adw.ComboRow()
        self.theme_row.set_title(_("Mode"))

        theme_store = Gtk.StringList()
        theme_store.append(_("Auto"))
        theme_store.append(_("Light"))
        theme_store.append(_("Dark"))

        self.theme_row.set_model(theme_store)

        self.monet_theming_expander.add_row(self.theme_row)

    def _on_option_changed(self, *_args):
        # Live-refresh only when there is already a wallpaper to work from.
        if self.monet_image_file:
            self.on_apply_button_clicked()

    @Gtk.Template.Callback()
    def on_apply_button_clicked(self, *_args):
        if self.monet_image_file:
            try:
                source_color = Monet().generate_source_color(self.monet_image_file)

                mode = {0: "auto", 1: "light", 2: "dark"}.get(
                    self.theme_row.props.selected, "auto"
                )
                variant = self._variant_keys[self.variant_row.props.selected]
                contrast = CONTRAST_LEVELS[
                    self._contrast_keys[self.contrast_row.props.selected]
                ]

                self.app.custom_css_group.reset_buffer()

                self.app.update_theme_from_monet(
                    source_color, mode, variant, contrast
                )
            except (OSError, AttributeError, ValueError) as e:
                logging.error("Failed to generate Monet palette", exc=e)
                self.parent.toast_overlay.add_toast(
                    Adw.Toast(title=_("Failed to generate Monet palette"))
                )
            else:
                logging.info("Monet palette generated successfully")
                self.parent.toast_overlay.add_toast(
                    Adw.Toast(title=_("Palette generated"))
                )
        else:
            logging.error("Input image for Monet generation not selected")
            self.parent.toast_overlay.add_toast(
                Adw.Toast(title=_("Select an image first"))
            )

    @Gtk.Template.Callback()
    def on_file_chooser_button_clicked(self, *_args):
        self.monet_file_chooser.open(self.parent, None, self.on_monet_file_chooser_response)

    def on_monet_file_chooser_response(self, widget, result):
        file = self.monet_file_chooser.open_finish(result)
        image_basename = file.get_basename()
        self.monet_file_chooser_button.set_label(image_basename)
        self.monet_file_chooser_button.set_tooltip_text(image_basename)
        self.monet_image_file = file.get_path()
        self.on_apply_button_clicked()
