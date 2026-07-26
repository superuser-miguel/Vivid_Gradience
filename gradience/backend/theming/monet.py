# monet.py
#
# Change the look of Adwaita, with ease
# Copyright (C) 2022 Gradience Team
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

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf

from materialyoucolor.quantize import QuantizeCelebi
from materialyoucolor.score.score import Score
from materialyoucolor.hct import Hct
from materialyoucolor.dynamiccolor.material_dynamic_colors import MaterialDynamicColors
from materialyoucolor.scheme.scheme_vibrant import SchemeVibrant
from materialyoucolor.scheme.scheme_tonal_spot import SchemeTonalSpot
from materialyoucolor.scheme.scheme_expressive import SchemeExpressive
from materialyoucolor.scheme.scheme_fidelity import SchemeFidelity
from materialyoucolor.scheme.scheme_content import SchemeContent
from materialyoucolor.scheme.scheme_neutral import SchemeNeutral
from materialyoucolor.scheme.scheme_monochrome import SchemeMonochrome
from materialyoucolor.scheme.scheme_rainbow import SchemeRainbow
from materialyoucolor.scheme.scheme_fruit_salad import SchemeFruitSalad

from gradience.backend.models.preset import Preset
from gradience.backend.utils.colors import argb_to_color_code, adjust_brightness

from gradience.backend.logger import Logger

logging = Logger()


# Material You scheme variants surfaced in the UI. Insertion order is the order
# shown in the "Style" combo row; the first entry is the default.
SCHEME_VARIANTS = {
    "vibrant": SchemeVibrant,
    "tonal_spot": SchemeTonalSpot,
    "expressive": SchemeExpressive,
    "fidelity": SchemeFidelity,
    "content": SchemeContent,
    "neutral": SchemeNeutral,
    "monochrome": SchemeMonochrome,
    "rainbow": SchemeRainbow,
    "fruit_salad": SchemeFruitSalad,
}
DEFAULT_VARIANT = "vibrant"

# UI contrast presets -> materialyoucolor contrast_level (spec range -1.0..1.0).
CONTRAST_LEVELS = {
    "standard": 0.0,
    "medium": 0.5,
    "high": 1.0,
}
DEFAULT_CONTRAST = 0.0


class Monet:
    """Generate a Material You (Material 3) scheme from a wallpaper image.

    Uses the maintained ``materialyoucolor`` library (dynamic schemes with a
    selectable variant and contrast level), and GdkPixbuf to read the image so
    PNG/JPG/SVG all work through the runtime's own loaders.
    """

    def __init__(self):
        self.source = None

    def generate_source_color(self, image_path: str) -> int:
        """Quantize a wallpaper and score it down to a single seed color (ARGB)."""
        if image_path.endswith(".xml"):
            # GNOME time-of-day wallpapers are XML definitions, not images.
            raise ValueError("XML wallpapers are not supported by the Monet engine")

        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                image_path, 128, 128, True
            )
        except Exception as e:
            logging.error("An error occurred while loading the Monet image.", exc=e)
            raise

        pixels = self._pixbuf_to_rgb_pixels(pixbuf)
        self.source = Score.score(QuantizeCelebi(pixels, 128))[0]
        return self.source

    @staticmethod
    def _pixbuf_to_rgb_pixels(pixbuf) -> list:
        """Flatten a GdkPixbuf into the list of (r, g, b) tuples QuantizeCelebi wants."""
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        channels = pixbuf.get_n_channels()
        rowstride = pixbuf.get_rowstride()
        data = pixbuf.get_pixels()

        pixels = []
        for y in range(height):
            row = y * rowstride
            for x in range(width):
                i = row + x * channels
                pixels.append((data[i], data[i + 1], data[i + 2]))
        return pixels

    @staticmethod
    def build_scheme(source: int, is_dark: bool, variant: str = DEFAULT_VARIANT,
                     contrast: float = DEFAULT_CONTRAST):
        scheme_class = SCHEME_VARIANTS.get(variant, SCHEME_VARIANTS[DEFAULT_VARIANT])
        return scheme_class(Hct.from_int(source), is_dark, contrast)

    def new_preset_from_scheme(self, scheme, is_dark: bool, name=None,
                               obj_only=False) -> Preset or None:
        preset = Preset()

        def role(role_name: str) -> int:
            return getattr(MaterialDynamicColors, role_name).get_argb(scheme)

        primary = role("primary")
        on_primary = role("onPrimary")
        secondary = role("secondary")
        secondary_container = role("secondaryContainer")
        on_secondary_container = role("onSecondaryContainer")
        tertiary = role("tertiary")
        tertiary_container = role("tertiaryContainer")
        on_tertiary_container = role("onTertiaryContainer")
        error = role("error")
        error_container = role("errorContainer")
        on_error_container = role("onErrorContainer")
        surface = role("surface")
        on_surface = role("onSurface")
        outline = role("outline")
        shadow = role("shadow")

        # A few derived tones are nudged differently for light vs dark, matching
        # the original Monet mapping.
        if not is_dark:
            view_factor, sidebar_factor = 1.5, 1.1
            shade_alpha, scrollbar = "0.07", argb_to_color_code(outline)
        else:
            view_factor, sidebar_factor = 0.5, 0.8
            shade_alpha, scrollbar = "0.36", argb_to_color_code(outline, "0.5")

        variable = {
            "accent_color": argb_to_color_code(primary),
            "accent_bg_color": argb_to_color_code(primary),
            "accent_fg_color": argb_to_color_code(on_primary),
            "destructive_color": argb_to_color_code(error),
            "destructive_bg_color": argb_to_color_code(error_container),
            # Avoid using .onError as it causes contrast issues
            "destructive_fg_color": argb_to_color_code(on_error_container),
            "success_color": argb_to_color_code(tertiary),
            "success_bg_color": argb_to_color_code(tertiary_container),
            "success_fg_color": argb_to_color_code(on_tertiary_container),
            "warning_color": argb_to_color_code(secondary),
            "warning_bg_color": argb_to_color_code(secondary_container),
            "warning_fg_color": argb_to_color_code(on_secondary_container),
            "error_color": argb_to_color_code(error),
            "error_bg_color": argb_to_color_code(error_container),
            # Avoid using .onError as it causes contrast issues
            "error_fg_color": argb_to_color_code(on_error_container),
            "window_bg_color": argb_to_color_code(surface),
            "window_fg_color": argb_to_color_code(on_surface),
            "view_bg_color": argb_to_color_code(adjust_brightness(secondary_container, view_factor)),
            "view_fg_color": argb_to_color_code(on_surface),
            "headerbar_bg_color": argb_to_color_code(secondary_container),
            "headerbar_fg_color": argb_to_color_code(on_secondary_container),
            "headerbar_border_color": argb_to_color_code(on_surface, "0.8"),
            "headerbar_backdrop_color": "@window_bg_color",
            "headerbar_shade_color": argb_to_color_code(on_surface, "0.07"),
            "sidebar_bg_color": argb_to_color_code(adjust_brightness(secondary_container, sidebar_factor)),
            "sidebar_fg_color": argb_to_color_code(on_secondary_container),
            "sidebar_border_color": "@view_bg_color",
            "sidebar_backdrop_color": "@window_bg_color",
            "sidebar_shade_color": argb_to_color_code(on_surface, "0.07"),
            "card_bg_color": argb_to_color_code(primary, "0.05"),
            "card_fg_color": argb_to_color_code(on_secondary_container),
            "card_shade_color": argb_to_color_code(shadow, "0.07"),
            "thumbnail_bg_color": argb_to_color_code(secondary_container),
            "thumbnail_fg_color": argb_to_color_code(on_secondary_container),
            "dialog_bg_color": argb_to_color_code(secondary_container),
            "dialog_fg_color": argb_to_color_code(on_secondary_container),
            "popover_bg_color": argb_to_color_code(secondary_container),
            "popover_fg_color": argb_to_color_code(on_secondary_container),
            "shade_color": argb_to_color_code(shadow, shade_alpha),
            "scrollbar_outline_color": scrollbar,
        }

        if obj_only == False and not name:
            raise AttributeError("You either need to set 'obj_only' property to True, or add value to 'name' property")

        if obj_only:
            if name:
                preset.new(variables=variable, display_name=name)
            else:
                preset.new(variables=variable)
            return preset

        if obj_only == False:
            preset.new(variables=variable, display_name=name)

            try:
                preset.save_to_file()
            except OSError:
                raise
