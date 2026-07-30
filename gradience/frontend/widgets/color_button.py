# color_button.py
#
# Change the look of Adwaita, with ease
# Copyright (C) 2026, Gradience Team
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

from gi.repository import Gtk, Gdk, GLib, GObject

from gradience.frontend.schemas.preset_schema import preset_schema


class GradienceColorButton(Gtk.MenuButton):
    """A drop-in stand-in for Gtk.ColorDialogButton whose popover offers the
    palette of the preset being edited before falling back to the system
    color dialog.

    Gtk.ColorDialog exposes no palette API at all, so the preset's own
    colors cannot be shown inside the system dialog; they are offered one
    click earlier instead. The `rgba` property and set_dialog() mirror the
    ColorDialogButton API that option_row and palette_shades already use.
    """

    __gtype_name__ = "GradienceColorButton"

    rgba = GObject.Property(type=Gdk.RGBA)

    SWATCH = 22          # popover swatch size, px
    SHADES = 5

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.dialog = None

        start = Gdk.RGBA()
        start.parse("rgba(0,0,0,0)")
        self.props.rgba = start

        self.preview = Gtk.DrawingArea(content_width=26, content_height=15)
        self.preview.set_draw_func(self._draw_swatch_func(lambda: self.props.rgba))
        self.set_child(self.preview)
        self.connect("notify::rgba", lambda *_: self.preview.queue_draw())

        self.set_create_popup_func(self._rebuild_popover)

    # -- ColorDialogButton API compatibility

    def set_dialog(self, dialog):
        self.dialog = dialog

    def get_dialog(self):
        return self.dialog

    def set_rgba(self, rgba):
        # ColorDialogButton swallows same-value sets before notifying, and the
        # call sites lean on that: update_shades reacts to notify::rgba by
        # setting every shade again, which is a same-value cycle. A property
        # that notifies unconditionally turns startup into a 100% CPU spin.
        current = self.props.rgba
        if current is not None and rgba is not None and current.equal(rgba):
            return
        self.props.rgba = rgba

    def get_rgba(self):
        return self.props.rgba

    # -- popover

    def _rebuild_popover(self, *_args):
        # Rebuilt on every open: the palette changes under us whenever the
        # user loads a preset or edits a shade, and this is cheaper than
        # tracking those edits from every color button in the window.
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                      margin_top=10, margin_bottom=10,
                      margin_start=10, margin_end=10)

        app = Gtk.Application.get_default()
        palette = getattr(app, "palette", None) or {}
        grid = self._palette_grid(palette)

        if grid is not None:
            title = Gtk.Label(label=getattr(app, "preset_name", "") or _("Palette"),
                              xalign=0)
            title.add_css_class("heading")
            box.append(title)

            subtitle = Gtk.Label(label="Vivid Gradience", xalign=0)
            subtitle.add_css_class("caption")
            subtitle.add_css_class("dim-label")
            box.append(subtitle)

            box.append(grid)
            box.append(Gtk.Separator(margin_top=2, margin_bottom=2))

        custom = Gtk.Button(label=_("Custom…"))
        custom.connect("clicked", self._on_custom_clicked)
        box.append(custom)

        popover = Gtk.Popover()
        popover.set_child(box)
        self.set_popover(popover)

    def _palette_grid(self, palette):
        grid = Gtk.Grid(row_spacing=2, column_spacing=2)
        filled = False
        for col, ramp in enumerate(preset_schema["palette"]):
            prefix, title = ramp["prefix"], ramp["title"]
            shades = palette.get(prefix, {})
            for row in range(1, self.SHADES + 1):
                value = shades.get(str(row), "")
                rgba = Gdk.RGBA()
                if not value or not rgba.parse(value):
                    continue
                filled = True
                swatch = Gtk.Button(tooltip_text=f"@{prefix}{row} · {value}")
                swatch.add_css_class("flat")
                area = Gtk.DrawingArea(content_width=self.SWATCH,
                                       content_height=self.SWATCH)
                area.set_draw_func(self._draw_swatch_func(lambda c=rgba: c))
                swatch.set_child(area)
                swatch.connect("clicked", self._on_swatch_clicked, rgba)
                grid.attach(swatch, col, row - 1, 1, 1)
        return grid if filled else None

    def _on_swatch_clicked(self, _button, rgba):
        self.popdown()
        self.set_rgba(rgba)

    def _on_custom_clicked(self, _button):
        self.popdown()
        dialog = self.dialog or Gtk.ColorDialog(title=_("Select a color"),
                                                modal=True, with_alpha=True)
        dialog.choose_rgba(self.get_root(), self.props.rgba, None,
                           self._on_custom_chosen)

    def _on_custom_chosen(self, dialog, result):
        try:
            rgba = dialog.choose_rgba_finish(result)
        except GLib.Error:  # dismissed
            return
        if rgba is not None:
            self.set_rgba(rgba)

    # -- drawing

    @staticmethod
    def _draw_swatch_func(get_rgba):
        def draw(_area, cr, width, height):
            rgba = get_rgba()
            radius = 4
            # rounded-rect path
            cr.new_sub_path()
            cr.arc(width - radius, radius, radius, -1.5708, 0)
            cr.arc(width - radius, height - radius, radius, 0, 1.5708)
            cr.arc(radius, height - radius, radius, 1.5708, 3.1416)
            cr.arc(radius, radius, radius, 3.1416, 4.7124)
            cr.close_path()
            if rgba.alpha < 1.0:
                # checkerboard so partial alpha is visible for what it is
                cr.save()
                cr.clip_preserve()
                cr.set_source_rgb(0.85, 0.85, 0.85)
                cr.paint()
                cr.set_source_rgb(0.55, 0.55, 0.55)
                step = 5
                for x in range(0, width, step):
                    for y in range(0, height, step):
                        if (x // step + y // step) % 2:
                            cr.rectangle(x, y, step, step)
                cr.fill()
                cr.restore()
            cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, rgba.alpha)
            cr.fill_preserve()
            # hairline border keeps near-white swatches from vanishing
            cr.set_source_rgba(0, 0, 0, 0.15)
            cr.set_line_width(1)
            cr.stroke()
        return draw
