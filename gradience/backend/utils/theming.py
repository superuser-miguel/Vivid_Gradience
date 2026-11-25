# theming.py
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

from gradience.backend.models.preset import Preset
from gradience.backend.utils.contrast import readable_variables


theming_warning_start = """/*
Generated with Vivid Gradience

Issues caused by theming should be reported to the Vivid Gradience repository, and not to upstream

https://github.com/superuser-miguel/Vivid_Gradience
*/

"""

theming_warning_end = """/*
Generated with Vivid Gradience end
*/
"""

# Controls an app draws over a backdrop it paints itself. Their backdrop
# ignores the preset, but their icons and labels inherit the preset's
# foreground, so a preset can leave them unreadable (dark text on a dark
# scrim). Both sides are pinned here to what the upstream apps intend:
# light controls on a dark scrim, whatever the preset or the system scheme.
#
#   Loupe:    the previous/next and zoom pills. The pill follows the system
#             scheme; the buttons inside are plain flat buttons. The class
#             is matched bare: Loupe's image view has no CSS name of its own
#             to scope it by.
#   Snapshot: the control frames and the gallery header bar, a black scrim
#             over the viewfinder. Upstream relies on forcing the dark scheme
#             to get a white foreground, which named colours override.
app_overlay_css = """/* Controls drawn over an app's own backdrop */
.osd-box {
  background-color: rgba(0, 0, 0, 0.65);
  color: rgba(255, 255, 255, 0.9);
}
camera .controlsframe,
gallery .controlsframe,
gallery headerbar {
  color: white;
}

"""

def generate_gtk_css(app_type: str, preset: Preset) -> str:
    palette = preset.palette
    custom_css = preset.custom_css
    # Role colours the toolkit draws as text are measured, not trusted: any
    # that would fall below WCAG AA on the surfaces they sit on is moved
    # until it reads. Colours that already pass are written exactly as the
    # preset has them.
    variables, _ = readable_variables(preset.variables, palette)

    gtk_css = theming_warning_start

    for key in variables.keys():
        gtk_css += f"@define-color {key} {variables[key]};\n"

    for prefix_key in palette.keys():
        for key in palette[prefix_key].keys():
            gtk_css += f"@define-color {prefix_key + key} {palette[prefix_key][key]};\n"

    if app_type == "gtk4":
        gtk_css += "\n" + app_overlay_css

    gtk_css += theming_warning_end

    gtk_css += custom_css.get(app_type, "")

    return gtk_css
