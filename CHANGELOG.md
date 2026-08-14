# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.1] - 2026-08-14

### Added

- The variables-vs-pin cross-check is a command now:
  `tools/check-firefox-pin.py` diffs the Firefox engine's `--gnome-*`
  variables and the Theme Options schema against the pinned
  firefox-gnome-theme release (from the app's own cache, a stamped
  profile, or `--fetch`), and fails on any seam that would break in
  silence — a written variable the release never reads, a `var()` with no
  definition, a feature pref without a switch, or a switch without a
  feature. `--tag` tries a candidate release before the pin moves.

### Fixed

- The About dialog no longer claims the project's inherited years under the
  fork's name. It credited "Copyright © 2022-2026 superuser-miguel", covering
  years that were the Gradience Team's work; it now credits both, matching the
  convention already used in the source headers. Three more files carried the
  same mistake from the original rebrand — the DOAP announced the project as
  "Gradience", `MAINTAINERS.md` named the wrong maintainer for the upstream it
  forked from, and `CODEOWNERS` was not valid syntax and matched nothing.

- The Firefox engine no longer writes `--gnome-view-background`: v150
  defines it in its palette files but no rule reads it, so the value never
  landed anywhere. Found by the new cross-check on its first run — the
  hand-done prune of eleven dead variables had missed this twelfth.

## [0.6.0] - 2026-08-13

### Added

- The Firefox engine can now install
  [firefox-gnome-theme](https://github.com/rafaelmardojai/firefox-gnome-theme)
  itself — the manual prerequisite is gone. When none of the profiles you
  have switched on has the theme, Apply offers to install a pinned,
  project-tested release (v150) into them and apply the preset in one go; a
  button on the Detected Profiles row installs into the remaining ones, or
  updates the app's own installs when the pin moves. Installs are wired
  exactly as
  upstream's script does it: the theme tree in `chrome/firefox-gnome-theme`,
  `@import` lines first in `userChrome.css` / `userContent.css`, and the
  required prefs appended to `user.js` inside fenced comments.

  Every install the app makes carries a stamp file; uninstalling removes
  precisely those installs — tree, imports and prefs block — and nothing
  else. A copy you installed yourself has no stamp and is never updated,
  uninstalled or touched, and your own `userChrome.css` rules and `user.js`
  prefs survive both install and uninstall. The release is cached after the
  first download, so later installs work offline. This is the one deliberate
  exception to the report-don't-install rule: not a system component, just
  files in a profile directory the engine already writes to.

- A Theme Options row on the Firefox Engine, opening the Firefox GNOME
  Theme's own optional features as switches — all 19 of them, from showing
  the List All Tabs button to OLED black, tabs as headerbar and system
  icons. The theme ships every one of them off and reads them straight out
  of `user.js`, so until now they were only reachable by hand-editing a file
  the app also writes to; the List All Tabs button being off by default is
  why Firefox's tab groups had no way in at all.

  The switches are seeded from the profiles themselves, so a pref you set by
  hand shows up already on, and they are written back into a fenced block of
  their own — separate from the required prefs, so your options survive a
  theme update and your own lines outside the fences are never rewritten.
  Options apply to every switched-on profile that has the theme.

- The Library window (Bookmarks and History) and Firefox's profile windows
  now follow the preset. Neither has ever been themeable: the Library paints
  its surfaces with system colours and draws some widgets natively, and the
  profile pages resolve their design tokens to `Canvas`, `Field` and
  `AccentColor` on Linux — so both asked GTK, and libadwaita answered with
  stock Adwaita regardless of the preset. Naming those surfaces directly
  outranks the system default, which is all it took. Covers the Library's
  toolbar, sidebar, list and details pane including tree selection, and
  `about:profilemanager` along with the new, edit and delete profile pages.

- The engine now also writes `--gnome-window-color` and
  `--gnome-sidebar-background`, which the theme reads in twenty-four places
  and the engine had never set — window text and sidebars were falling back
  to the theme's own colours rather than the preset's.

- The Firefox engine now writes the preset into Firefox's own about: pages
  as well as its windows. Settings, Add-ons, Passwords, Downloads, the print
  dialog and the rest resolve their colours from GTK system colours, which
  libadwaita answers with stock Adwaita — so they sat in Firefox's default
  palette next to a fully themed browser. The engine now writes a second
  stylesheet, `customContent.css`, through the hook firefox-gnome-theme
  provides for exactly this, and names those pages one by one rather than
  at `:root`, so no rule of ours can reach an ordinary website.

- The Firefox engine also writes `--gnome-view-background`,
  `--gnome-card-background` and `--gnome-secondary-sidebar-background`,
  which the theme reads for content areas, cards and secondary sidebars and
  the engine had never set.

- Nine more Casts, taking the family to sixteen: Undying (muted taupe with
  a teal accent), Valentines (deep maroon under hot pink), Potentia (a
  light theme of pale blue and amber), Lotus (navy with aqua), Easter (the
  family's first pastel light — lavender with a deep orchid accent),
  Hallows Eve (plum with orange), Gamma (navy with chartreuse), Rhino
  Heirloom (warm taupe with the palette's own electric cyan) and Storm
  (slate with salmon). Each is derived from its source palette the same
  way the first seven were, and every foreground/background pair clears
  WCAG AA.

### Changed

- The Firefox engine now themes the profiles you choose, one switch each,
  instead of every profile it can find. People theme profiles apart so they
  can tell one window from another at a glance, and one preset across all of
  them flattened exactly that — so a profile that already has a Firefox theme
  of its own is switched off the first time the engine sees it.

  The switch is the whole engine, not just its colours. Switching a profile
  off takes the generated stylesheets out and uninstalls the Firefox GNOME
  Theme with them; switching it back on installs from the cached release and
  writes the preset, so the switch is its own undo and no download is needed
  either way. A copy of the theme you installed yourself carries no stamp and
  is never installed over or removed — only the colours go in, through the
  hook the theme sets aside for them. Your own `userChrome.css` rules and any
  `user.js` prefs outside the app's fences survive both directions.

  Install, Apply, Options and the summary all follow the switches. Remove
  Colours and Uninstall still cover every profile, because they are the way
  back out.

  Profiles are listed under a heading per browser rather than in one flat
  list, because Firefox and LibreWolf both call their first profile
  "default" and two identical rows are unreadable. The heading names the
  browser properly — LibreWolf, not Librewolf — and spells out the
  packaging only when the same browser is found in more than one place, so
  "LibreWolf (Flatpak)" appears exactly when it distinguishes something.
  Every row carries its profile's full path as a tooltip, for the case where
  two profiles of one browser share a name and nothing else can tell them
  apart.

- The Firefox engine's two destructive buttons say what they do. The first
  was an unlabelled row holding a "Remove Theme" button that removed only
  the generated colours; it is now "Preset Colours → Remove Colours", next
  to "Firefox GNOME Theme → Uninstall".

- The Firefox GNOME Theme pin moves from v149.1 to v150, which is where
  upstream fixed the tab group colours themselves — along with two dozen
  other fixes for the misalignments that show up on current Firefox. The
  app offers to update installs it made; copies you installed yourself are
  still never touched.

- The Firefox engine no longer writes eleven colours the theme does not
  read. `--gnome-toolbar-color`, the four `--gnome-inactive-toolbar-*` and
  `--gnome-inactive-tabbar-*` variables, both `--gnome-switch-*-slider-*`,
  `--gnome-tabbar-tab-background`, `--gnome-browser-before-load-background`
  and `--gnome-button-destructive-action-background` were inherited from
  the plugin the engine replaced and had already stopped landing anywhere.
  Nothing changes in the browser; the generated stylesheet is just honest
  about what it reaches now.

### Fixed

- Whole sections of the interface could not be translated in any of the 27
  languages. The list of files gettext reads had drifted out of date, so
  every string in the Firefox engine, the icon engine, the desktop settings
  and the custom-themes group was shipped untranslated regardless of your
  locale. The list is now generated from what the source actually contains.

- The application's metainfo failed validation because of an empty
  translation URL — this fork has no translation platform, so the entry has
  been removed rather than left blank. The developer entry was also moved to
  the form current AppStream expects.

- Tab groups in Firefox's all-tabs menu lost their colours: every group's
  swatch came out in the preset's toolbar icon colour and saved groups
  vanished altogether, because firefox-gnome-theme tints every toolbar icon
  and the group swatch is one. The Firefox engine now hands the swatch back
  the colour Firefox picked for that group, outline included.

- Firefox's new tab page had never taken the preset's colours. The engine
  wrote a block of forty-eight new-tab variables into `customChrome.css`,
  which is a stylesheet for *chrome* documents — the new tab is content, so
  the rules could not apply and the page kept firefox-gnome-theme's own
  dark background whichever preset was loaded. The block now lives in
  `customContent.css`, where the theme keeps its own new-tab rules.

## [0.5.0] - 2026-07-30

### Added

- A Firefox Engine on the Theming tab. It writes the preset's colours into
  every browser profile that has
  [firefox-gnome-theme](https://github.com/rafaelmardojai/firefox-gnome-theme)
  installed — Firefox, LibreWolf and Waterfox, packaged natively, as Flatpak
  or as Snap. When no profile has the theme, the app says what is missing and
  links to the project page rather than installing anything.

  The port fixes what the retired plugin got wrong: tab backgrounds were
  hardcoded white overlays (invisible on light presets) and now derive from
  the preset's foreground; the `about:home` / `about:newtab` page was
  Firefox's stock dark palette written as literals and now follows the preset;
  profiles with absolute paths in `profiles.ini` were silently mishandled; and
  a `customChrome.css` not written by Vivid Gradience is left untouched — it
  is the user's customisation hook, not ours.

- The colour picker now offers the palette of the preset being edited: the
  colour button on every row opens a swatch grid of the preset's nine ramps
  under the preset's name, with the system colour dialog behind a Custom…
  button. Gtk.ColorDialog has no palette API, so the swatches sit one click
  before it rather than inside it.

### Added (continued)

- An Icon Engine on the Theming tab — the recoloured "pseudo-Adwaita" icon
  theme, previously a script, is now a click. Apply generates the theme from
  the preset's best-scoring palette ramp (contrast against the view first,
  then nearest the accent), writes it to `~/.local/share/icons`, ships the
  Adwaita attribution alongside, and selects it; Remove selects the default
  again and deletes the generated directory — unless the user has since
  chosen a different icon theme, which is left alone. The group shows which
  ramp would be used and why before anything is applied.

### Added (Tweaks absorption)

- A Desktop group on the Theming tab with the pickers inherited from GNOME
  Tweaks: legacy GTK 3 theme, cursor theme, a Dark Style switch and the
  window-button layout. Every one is a plain gsettings key — instantly
  reversible. The GTK 3 picker carries the check Tweaks never had: when the
  chosen theme has no `org.gtk.Gtk3theme` Flatpak extension, a warning
  explains that sandboxed applications will silently fall back to Adwaita
  while host applications use the theme, and names the install command.

### Added (safety)

- Apply now recognises a stylesheet it did not write. When
  `~/.config/gtk-{3.0,4.0}/gtk.css` exists without the Vivid Gradience
  marker — most likely an installed theme — a dialog names the file and its
  size and offers three ways out: move it into the theme library and then
  apply, back it up and replace it, or cancel. This closes the one silent
  data-loss path in the app.

- A Custom Themes group on the Advanced page: the user's theme library in
  `~/.local/share/themes`, showing what each theme provides
  (gtk-3.0 / gtk-4.0 / gnome-shell), with folder import and removal.
  Stylesheets rescued by the Apply dialog land here, named
  `imported-<toolkit>-<date>`, with a README recording where they came from.

- Applying a preset also leans `org.gnome.desktop.interface accent-color`
  (GNOME's nine-value system accent) toward the preset's accent by hue, so
  desktop chrome that follows the system accent stops fighting the theme.

### Changed

- "Restore previous preset" now reads the same snapshot store as "Restore
  original". Apply used to maintain two parallel backups — the versioned
  store and a single-slot `gtk.css.bak` — and the restore button read only
  the latter. The `.bak` file is no longer written; a leftover one is still
  honoured when the store is empty, so the first restore after upgrading
  keeps working. A failed restore also shows its error toast again — the
  handler was catching the wrong exception type.

### Fixed

- The icon engine's ramp choice now actually honours "nearest the accent".
  The tie-break checked ramp visibility against a list that CPython empties
  for the duration of the sort, so it silently ranked by raw contrast alone —
  a teal-accented scheme got red folders because red cleared the view by an
  extra 0.04, while the output claimed "nearest accent". The condition is
  now decided before sorting.

- One cast row no longer serves two palette ramps. Five of the seven cast
  presets had a duplicated ramp (Rot's purple_ was byte-identical to its
  light_, and friends): the generator assigned the lightness extremes to
  light_/dark_ without checking what the hue matching had already claimed.
  The named variables — surfaces, accent, status colours — are unchanged in
  all seven; only ramp assignments moved, always to another row of the same
  cast.

### Documentation

- README, roadmap and site brought in line with what actually shipped: GNOME
  Shell theming as a working feature rather than a plan, the recoloured icon
  theme as a script that is not yet in the app, and setup instructions that name
  the Flatpak theme extension — the missing piece that silently splits a desktop
  between host and sandboxed applications.
- The time-of-day cycle entry now records what a running desktop will accept:
  which settings reach live applications, that GTK 4 parses
  `@media (prefers-color-scheme)` and ignores it, and that the cycle needs its
  own storage rather than the backup store.
- The Findings page is rewritten as notes for anyone theming a GNOME desktop,
  not just a log of this project's surprises. Five new sections: what actually
  needs restarting (and what does not), why a Flatpak resolves themes separately
  from the host, why GTK 3's built-in Adwaita cannot be recoloured at all,
  recolouring Adwaita's icons without forking them, and which colour
  distinctions survive being seen on someone else's screen.

## [0.4.0] - 2026-07-29

### Added

- `tools/icons-from-preset.py` — generate a recoloured "pseudo-Adwaita" icon
  theme from a preset, so folders stop being Adwaita blue under a themed
  desktop. 35 icons, 29 blues mapped through a luminance curve built from a
  palette ramp; everything else inherits from Adwaita untouched. The ramp is
  chosen by what the folder *becomes* — scored for visibility against
  `view_bg_color` first, then for closeness to the accent. Nothing is applied
  unless you pass `--apply`.

- `tools/shift-preset-hue.py` — lean a preset's colour family onto a different
  hue. Rotates the signature fully, the named palette ramps partway, and the
  status colours not at all (a warning that rotates off amber stops reading as
  a warning).

### Changed

- **GNOME Shell theming works again**, on any Shell version, and applies to a
  running session without logging out. The engine no longer vendors GNOME's
  stylesheet sources per release and compiles them with libsass — the approach
  that capped it at GNOME 45. It now rethemes the stylesheet the installed
  Shell already ships, remapping its colours onto the preset's surfaces by
  luminance. On GNOME 50 that is ~3,300 lines and 51 distinct colours, none of
  which have to be known in advance.

  Shell accents are no longer restricted to the nine values of
  `org.gnome.desktop.interface accent-color`: `-st-accent-color` is read-only,
  but a generated stylesheet can substitute a literal for it, and the Shell's
  own colour functions keep working on the substitution.

- **Bluebell** leans to a deeper cyan and **Lilac Mist** to a carbazole violet.
  They sat 6.2 dE apart and read as the same pastel; they are now 25.4 apart.
  Both still clear WCAG AA. The families inherited from upstream are
  deliberately left alone — their near-twins are the point once a scheme can be
  cycled within one family.

### Documentation

- Two findings added to the site: GNOME Shell can be rethemed on a running
  session with no logout, and X11 titlebars answer to ordinary `headerbar` CSS
  rather than the twelve `wm_*` colours named for them — including the
  application that prompted the investigation turning out not to be an X11
  client at all.
- Roadmap: environment checks that report a broken base-theme setup rather than
  silently rendering onto it; GNOME Shell engine reclassified as needing a
  rewrite rather than a revival.

## [0.3.0] - 2026-07-28

### Added

- Three original preset families, 23 schemes in all, taking the bundled count
  from 53 to **76**. They lead the gallery, ahead of the families inherited
  from upstream.
  - **Casts** — Eminence, Hatred, Daybreak, Fear, Conquest, Agony, Rot.
    Derived from source colour palettes: every surface, accent and foreground
    is an unmodified swatch from the palette it came from, with contrast met
    by choosing a different swatch rather than altering one.
  - **Pastel** — Cotton Candy, Sea Glass, Powder Puff, Lilac Mist, Peach Fizz,
    Buttercream, Sage Linen, Bluebell.
  - **Neon** — Neon Tokyo, Vaporwave, Acid Rave, Cyberlime, Neon Tangerine,
    Voltage, Ultraviolet, Infrared.

  Every foreground/background pair in all 23 clears WCAG AA (4.5:1); the
  lowest sits at 4.61.

- **Live preview** in the Colors tab — a schematic window that redraws on every
  edit, before Apply, marking any text that falls below WCAG AA. Drawn rather
  than built from real widgets because libadwaita only reads named-colour
  overrides from the stylesheet loaded at startup.

- `tools/palette-from-image.py` — extract a palette from a swatch-grid
  screenshot
- `tools/preset-from-cast.py` — build a preset from an extracted palette
- `tools/audit-contrast.py` — score every bundled preset against WCAG

### Changed

- Every status and accent label across the bundled schemes now meets WCAG AA.
  Only label colours changed — no scheme's own fills were touched, so each
  keeps the colours it is recognised by. Solarized Light is deliberately left
  below AA: its low contrast is the defining characteristic of that scheme.

### Fixed

- `get_shell_colors()` no longer raises on a preset missing a variable, and
  drops a dead special case for `panel_bg_color` — a key that does not exist in
  the Shell schema, reading a default from an index that holds `osd_fg_color`.
- Shell surface colours that are `rgba()` or `@references` now resolve properly.
  Treating them as unusable made light schemes take white as their foreground
  and render the whole Shell mid-grey.

- Stop the greeting on the first-run Welcome screen from wrapping mid-name

## [Unfiled — shipped in 0.1.0-0.2.0, never recorded under a version]

### Changed

- Update runtime to GNOME 50 (latest stable)
- Rename app-id to valid RDNN `io.github.superuser_miguel.VividGradience`
  (old id had a hyphen in a non-final segment, which Flatpak rejects)

### Fixed

- Fix `IndentationError` crash in the About dialog (`setup` had escaped the class body)
- Rename icon files that were still named after upstream, unbreaking the Flatpak build

## [0.8.0] - 2025-XX-YY

### Out of support

- Support for GNOME Shell theming (supported up to 44)
- Support for plugins

### Added

- New, refreshed design for `Theming` tab
- Preferences options for enabling built-in Theme Engines

### Changed

- Update runtime to GNOME 49
- Move reset and restore preset options to preferences

### Fixed

- Improve contrasts in Monet generated error/destructive colors
- Don't fail at compilation if host doesn't have `git` installed
- Don't fail at resetting presets if `gtk.css` isn't found
- Support for libadwaita sidebar

## [0.4.1] - 2023-03-05

### Changed

- Only configure local CLI if `buildtype` is set to debug
- Margins in popup explanations and some other widgets
- Object names in preferences window
- Translation updates

### Fixed

- Local CLI executable making issues with Fedora CI
- Theme variant menu in Monet Engine not working with non-english locales
- Applied temporary patch for `CssProvider.load_from_data()` new behavior in GTK 4.9

## [0.4.0] - 2023-02-09

### Added

- Command-line interface, useful for creating scripts or for those who prefer terminal tools
- New logging facility, with easier to understand error messages

### Removed

- Preset preview button and "Repositories" tab in Preset Manager have been removed due to lack of proper implementation

### Changed

- Now Gradience warns user when switching to other presets, if current one has unsaved changes
- Gradience started internally use hexadecimal color values or RGBA formatted colors if transparency is provided
- Start moving out remaining backend functions from frontend modules
- Codebase is now linted by pylint
- Translation updates

### Fixed

- Fixed color palette leaking into preset variables in some rare occasions
- Fixed list index out of range error in Custom CSS editor
- Fixed sorting in "Explore" tab of Preset Manager not working with non-English locales

## [0.3.3] - 2022-12-03

## Changed

- The Firefox GNOME theme plugin now parses profiles from `profiles.ini`
- Theme Preview button is accessible again
- Plugin row now has the correct controls placement
- Codebase structure has been refactored
- Improved details tab in About dialog
- Added new "Log out" dialog logic
- Updated translations

## [0.3.2] - 2022-11-20

### Changed

- The Firefox GNOME theme plugin now correctly parses installations with multiple profiles
- Added mnemonics for dialogs
- Save is now a default response in dialogs
- Plugin rows now look cleaner and are correctly placed
- File picker is now modal and sticks to the parent window
- <kbd>Esc</kbd> now closes dialogs and Preset Manager
- Grandience can now be closed with <kbd>Ctrl</kbd> + <kbd>Q</kbd>
- "Favourite(s)" was renamed to "Favorite(s)"
- Тransitioned from `cssutils` library to an in-house solution
- Presets are now removed correctly
- The internal structure was refactored
- Various typos were fixed
- The `README.md` was fully rewritten
- All screenshots were taken in high resolution
- New and updated translations

### Fixed

- Fixed issues with the CSS parser
- Fixed an issue with presets always being saved as User.json

## [0.3.1] - 2022-10-08

### Added

- Added ability to star preset to display it in Palette menu
- Added filter to search presets by preset repositories in Preset Manager
- Added "No Preferences" window for use in plugins
- Added "Log Out" dialog showing after applying a preset

### Changed

- Updated Firefox GNOME Theme plugin
- Welcome screen have been improved
- Preset Manager window size has changed
- "Offline" and "Nothing Found" fallback pages have been added to Preset Manager
- Many strings were rewritten to follow GNOME HIG
- Switch from `aiohttp` to `libsoup3`
- Migrate to GNOME SDK 43
- All contributors have been added to "About" window
- Some symbolics have changed, removed unnecessary hardcoded symbolics
- New and updated translations

### Fixed

- Flatpak theme override is now fixed
- Margins in color info popovers are fixed

## [0.3.0] - 2022-09-23

### Added

- Added plugins support, this will allow users to create plugins for customizing other apps
- Added support for custom preset repositories, this allows creating your own remote selection of presets
- Added search feature to Preset Manager
- Added Quick Preset Switcher back, with it you can switch presets with less clicks

### Changed

- Preset Manager performance has significantly increased, presets are downloading much faster and app don't freeze on preset removal
- Preset Manager is attached to the main window
- Save dialog now shows up when you close app with unsaved preset
- Currently applied preset now auto-loads on app start-up
- Toasts are less annoying
- Added support for aarch64 builds

<!-- TODO: Below version changelogs aren't yet filled -->

## [0.2.2] - 2022-09-02

## [0.2.1] - 2022-08-30

## [0.2.0] - 2022-08-26

## [0.1.0] - 2022-08-12
