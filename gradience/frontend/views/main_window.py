# main_window.py
#
# Change the look of Adwaita, with ease
# Copyright (C) 2022-2023, Gradience Team
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

import json
from enum import Enum

from gi.repository import Gtk, Adw, Gio, Gdk, Pango

from gradience.backend.constants import rootdir, app_id, build_type

from gradience.frontend.widgets.shell_theming_group import GradienceShellThemingGroup
from gradience.frontend.widgets.monet_theming_group import GradienceMonetThemingGroup
from gradience.frontend.widgets.palette_shades import GradiencePaletteShades
from gradience.frontend.widgets.error_list_row import GradienceErrorListRow
from gradience.frontend.widgets.option_row import GradienceOptionRow
from gradience.frontend.schemas.preset_schema import preset_schema

from gradience.backend.logger import Logger

logging = Logger()


@Gtk.Template(resource_path=f"{rootdir}/ui/window.ui")
class GradienceMainWindow(Adw.ApplicationWindow):
    __gtype_name__ = "GradienceMainWindow"

    content_colors = Gtk.Template.Child("content-colors")
    content_theming = Gtk.Template.Child("content-theming")
    theming_stack = Gtk.Template.Child()
    shell_warning_banner = Gtk.Template.Child()
    content_plugins = Gtk.Template.Child("content-plugins")

    view_stack = Gtk.Template.Child()

    toast_overlay = Gtk.Template.Child()

    save_preset_button = Gtk.Template.Child("save-preset-button")
    errors_button = Gtk.Template.Child("errors-button")

    errors_list = Gtk.Template.Child("errors-list")
    presets_dropdown = Gtk.Template.Child("presets-dropdown")
    presets_menu = Gtk.Template.Child("presets-menu")
    presets_box = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.app = Gtk.Application.get_default()
        self.settings = Gio.Settings(app_id)

        self.style_manager = self.app.style_manager

        self.monet_image_file = None

        self.enabled_theme_engines = set(
            self.settings.get_value("enabled-theme-engines").unpack()
        )

        self.setup_signals()
        self.setup()

    def setup_signals(self):
        self.presets_dropdown.get_popover().connect("show",
            self.on_presets_dropdown_activate)

        self.connect("close-request",
            self.on_close_request)

        self.connect("unrealize",
            self.save_window_props)

    def switch_to_colors_page(self, *args):
        self.view_stack.set_visible_child_name("colors")

    def switch_to_theming_page(self, *args):
        self.view_stack.set_visible_child_name("theming")

    def switch_to_advanced_page(self, *args):
        self.view_stack.set_visible_child_name("plugins")


    def setup(self):
        # Set devel style
        if build_type == "debug":
            self.get_style_context().add_class("devel")

        self.setup_theming_page()
        self.setup_colors_group()
        self.setup_presets_gallery()

    # --- Presets gallery -------------------------------------------------

    BUILTIN_PRESET_SECTIONS = [
        ("Adwaita", ["adwaita", "adwaita-dark"]),
        ("Popular Themes", ["catppuccin-mocha", "catppuccin-latte",
                            "gruvbox-dark", "nord", "dracula",
                            "tokyo-night", "pretty-purple"]),
    ]

    def setup_presets_gallery(self):
        for title, slugs in self.BUILTIN_PRESET_SECTIONS:
            self.presets_box.append(self._build_preset_section(title, slugs))

    def _build_preset_section(self, title, slugs):
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        label = Gtk.Label(label=_(title), xalign=0)
        label.add_css_class("heading")
        section.append(label)

        flow = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE,
            homogeneous=True,
            min_children_per_line=2,
            max_children_per_line=4,
            row_spacing=12,
            column_spacing=12,
        )
        for slug in slugs:
            card = self._build_preset_card(slug)
            if card is not None:
                flow.append(card)
        section.append(flow)
        return section

    def _build_preset_card(self, slug):
        data = self._load_preset_data(slug)
        if data is None:
            return None

        name = data.get("name", slug)
        author = data.get("author", "")
        colors = self._preview_colors(data.get("variables", {}))

        preview = Gtk.DrawingArea(content_height=56, hexpand=True)
        preview.set_draw_func(self._draw_swatches, colors)

        name_label = Gtk.Label(label=name, xalign=0)
        name_label.add_css_class("heading")
        name_label.set_ellipsize(Pango.EllipsizeMode.END)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content.append(preview)
        content.append(name_label)
        if author:
            author_label = Gtk.Label(label=author, xalign=0)
            author_label.add_css_class("caption")
            author_label.add_css_class("dim-label")
            author_label.set_ellipsize(Pango.EllipsizeMode.END)
            content.append(author_label)

        button = Gtk.Button(child=content)
        button.add_css_class("card")
        button.add_css_class("activatable")
        button.set_tooltip_text(_("Apply “{}”").format(name))
        button.connect("clicked", self.on_preset_card_clicked, slug)
        return button

    def _load_preset_data(self, slug):
        try:
            gbytes = Gio.resources_lookup_data(
                f"{rootdir}/presets/{slug}.json", Gio.ResourceLookupFlags.NONE
            )
            return json.loads(gbytes.get_data().decode("utf-8"))
        except Exception as e:
            logging.error(f"Could not load bundled preset '{slug}': {e}")
            return None

    def _preview_colors(self, variables):
        colors = []
        for key in ("window_bg_color", "view_bg_color", "headerbar_bg_color",
                    "accent_bg_color", "window_fg_color"):
            value = variables.get(key, "")
            rgba = Gdk.RGBA()
            if value and rgba.parse(value):
                colors.append(rgba)
        return colors

    def _draw_swatches(self, area, cr, width, height, colors):
        if not colors:
            return
        band = width / len(colors)
        for i, color in enumerate(colors):
            cr.set_source_rgb(color.red, color.green, color.blue)
            cr.rectangle(i * band, 0, band + 1, height)
            cr.fill()

    def on_preset_card_clicked(self, _button, slug):
        self.app.load_preset_from_resource(f"{rootdir}/presets/{slug}.json")

    # TODO: Check if org.freedesktop.portal.Settings portal will allow us to \
    # read org.gnome.desktop.background DConf key
    # FIXME: Find purpose for this snippet
    '''def get_default_wallpaper(self):
        background_settings = Gio.Settings("org.gnome.desktop.background")
        if self.style_manager.get_dark():
            picture_uri = background_settings.get_string("picture-uri-dark")
        else:
            picture_uri = background_settings.get_string("picture-uri")
        logging.debug(picture_uri)
        if picture_uri.startswith("file://"):
            self.monet_image_file = Gio.File.new_for_uri(picture_uri)
        else:
            self.monet_image_file = Gio.File.new_for_path(picture_uri)
        image_basename = self.monet_image_file.get_basename()
        logging.debug(image_basename)
        self.monet_image_file = self.monet_image_file.get_path()
        #self.monet_file_chooser_button.set_label(image_basename)
        #self.monet_file_chooser_button.set_tooltip_text(self.monet_image_file)
        logging.debug(self.monet_image_file)
        # self.on_apply_button_clicked() # Comment out for now, because it always shows
        # that annoying toast on startup'''

    def on_close_request(self, *args):
        if self.app.is_dirty:
            logging.debug("Window close request")
            self.app.show_unsaved_dialog()
            return True
        self.close()

    def save_window_props(self, *args):
        win_size = self.get_default_size()

        self.settings.set_int("window-width", win_size.width)
        self.settings.set_int("window-height", win_size.height)

        self.settings.set_boolean("window-maximized", self.is_maximized())
        self.settings.set_boolean("window-fullscreen", self.is_fullscreen())

    def setup_theming_page(self):
        self.setup_shell_group()
        self.setup_monet_group()
        self.update_theming_view()

    def update_theming_view(self):
        # Show a StatusPage when no engines are enabled, the engine groups otherwise.
        has_engines = bool(self.enabled_theme_engines)
        self.theming_stack.set_visible_child_name("engines" if has_engines else "empty")
        self.shell_warning_banner.set_revealed("shell" in self.enabled_theme_engines)

    def setup_shell_group(self):
        self.shell_group = GradienceShellThemingGroup(self)

        if "shell" in self.enabled_theme_engines:
            self.content_theming.add(self.shell_group)

    def setup_monet_group(self):
        self.monet_group = GradienceMonetThemingGroup(self)

        if "monet" in self.enabled_theme_engines:
            self.content_theming.add(self.monet_group)

    def reload_theming_page(self):
        if self.shell_group.is_ancestor(self.content_theming):
            self.content_theming.remove(self.shell_group)

        if self.monet_group.is_ancestor(self.content_theming):
            self.content_theming.remove(self.monet_group)

        self.setup_shell_group()
        self.setup_monet_group()
        self.update_theming_view()

    def setup_colors_group(self):
        self.color_categories = []

        # Search field to filter the (many) named colors.
        self.colors_search = Gtk.SearchEntry(
            hexpand=True,
            placeholder_text=_("Search colors"),
        )
        self.colors_search.connect("search-changed", self.on_colors_search)
        search_group = Adw.PreferencesGroup()
        search_group.add(self.colors_search)
        self.content_colors.add(search_group)

        # Each color category becomes a collapsible ExpanderRow.
        categories_group = Adw.PreferencesGroup()
        for group in preset_schema["groups"]:
            category = Adw.ExpanderRow()
            category.set_name(group["name"])
            category.set_title(group["title"])
            if group.get("description"):
                category.set_subtitle(group["description"])

            variables = []
            for variable in group["variables"]:
                pref_variable = GradienceOptionRow(
                    variable["name"],
                    variable["title"],
                    variable.get("explanation"),
                    variable["adw_gtk3_support"],
                )
                category.add_row(pref_variable)

                pref_variable.connect_signals(update_vars=True)
                self.app.pref_variables[variable["name"]] = pref_variable

                searchable = f"{variable['title']} {variable['name']}".lower()
                variables.append((pref_variable, searchable))

            categories_group.add(category)
            self.color_categories.append(
                {"row": category, "title": group["title"].lower(), "variables": variables}
            )
        self.content_colors.add(categories_group)

        self.palette_group = Adw.PreferencesGroup()
        self.palette_group.set_name("palette_colors")
        self.palette_group.set_title(_("Palette Colors"))
        self.palette_group.set_description(
            _(
                "Named palette colors used by some applications. Default "
                "colors follow the "
                '<a href="https://developer.gnome.org/hig/reference/palette.html">'
                "GNOME Human Interface Guidelines</a>."
            )
        )
        for color in preset_schema["palette"]:
            palette_shades = GradiencePaletteShades(
                color["prefix"], color["title"], color["n_shades"]
            )
            self.palette_group.add(palette_shades)
            self.app.pref_palette_shades[color["prefix"]] = palette_shades
        self.content_colors.add(self.palette_group)

    def on_colors_search(self, entry):
        query = entry.get_text().strip().lower()

        for category in self.color_categories:
            title_match = query in category["title"]
            any_visible = False
            for row, searchable in category["variables"]:
                visible = (not query) or title_match or (query in searchable)
                row.set_visible(visible)
                any_visible = any_visible or visible
            category["row"].set_visible(any_visible)
            # Expand matching categories while searching; collapse when cleared.
            category["row"].set_expanded(bool(query) and any_visible)

        # The palette section isn't part of the named-color search.
        self.palette_group.set_visible(not query)

    def update_errors(self, errors):
        child = self.errors_list.get_row_at_index(0)
        while child is not None:
            self.errors_list.remove(child)
            child = self.errors_list.get_row_at_index(0)
        self.errors_button.set_visible(len(errors) > 0)
        for error in errors:
            self.errors_list.append(
                GradienceErrorListRow(error["error"], error["element"], error["line"])
            )

    def on_presets_dropdown_activate(self, *args):
        self.app.reload_user_defined_presets()
