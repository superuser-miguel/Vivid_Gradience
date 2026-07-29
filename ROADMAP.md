## Roadmap

If you'd like to see a new feature, open an issue or submit a PR.

### Immediate Goals

- [x] Working Flatpak targeting GNOME 48+ / runtime 50 (latest)
- [x] Automatically track new GNOME runtime releases
- [x] Signed releases + a hosted, auto-updating Flatpak repo (`flatpak update`),
      distributed independently of Flathub
- [ ] Modernize the UI — adopt current libadwaita composition:
  - [x] Wrap windows in `Adw.ToolbarView` (modern top/bottom-bar elevation)
  - [x] Add `Adw.Breakpoint` for an adaptive, resize-to-narrow layout
  - [x] Adopt newer rows: `Adw.SwitchRow`, `Adw.EntryRow` (no `SpinRow` needed)
  - [x] Declutter the header bar (now just Apply · Save + view switcher + menu)
  - [x] Raise the libadwaita floor (1.4 → 1.6)
  - [x] Searchable, collapsible color categories; reflowing palette swatches
  - [x] Theming empty-state `StatusPage`; shell warning `Banner`
  - [ ] Align spacing, margins, and icons with the GNOME HIG
- [ ] Verify all base theming features work with current libadwaita
- [ ] Clean up and modernize the codebase

### Base Features (inherited)

- [x] Customize named colors with color picker or text
- [x] Explanations for some named colors
- [x] Partial theme preview
- [x] Built-in presets for Adwaita and Adwaita Dark
- [x] Apply changes to Libadwaita, GTK 4 and GTK 3 applications
- [x] Load and create custom presets
- [x] View parsing errors
- [x] Customize palette colors
- [x] Add custom CSS code
- [x] Normalize color variables
- [x] Preset manager with community presets
- [x] Autoload theme from CSS

### Planned Features

- [x] Visual preset gallery — a dedicated Presets tab with color previews
- [x] Curated built-in themes — 75+ color schemes (Catppuccin, Gruvbox, Nord,
      Dracula, Rosé Pine, Everforest, Solarized, Tokyo Night, and the full Arc
      and Matcha families), plus the original Pastel, Neon and Cast sets,
      grouped into family sections in the gallery
- [ ] Palette editor — browse a colour cast and assign its swatches to theme
      roles (surfaces, accent) directly, with live preview and contrast
      warnings; `tools/preset-from-cast.py` does this non-interactively today
- [ ] Show user presets in the gallery (built-in schemes done)
- [ ] Color wheel for picking colors
- [ ] Import GTK 3/4 themes from external sources (OpenDesktop, GitHub, and others)
- [ ] Light/dark preset pairs **(high priority)**
- [ ] Time-of-day theme cycle — rotate 2–4 presets across the day **(important)**

  Design notes, from measuring what a running desktop will actually accept:

  - **Four of five channels update live.** `accent-color`, `color-scheme`,
    `icon-theme` and the Shell theme all reach running applications. Only
    `gtk.css` — our own 46 colors — does not; those are read once at startup.
  - **One stylesheet cannot hold both light and dark.** GTK 4 parses
    `@media (prefers-color-scheme: dark)` without complaint and then ignores it.
    Verified by rendering: the widget keeps its light color in both schemes.
  - **Crossing light↔dark mid-session is the dangerous transition.** Within a
    mode, an app that has not been reopened is merely wearing the wrong valid
    theme. Across modes it gets dark widgetry over light surfaces, because our
    `gtk.css` still asserts the old colors at higher priority.
  - **Its own storage, never `ThemeBackup`.** That store keeps ten rotating
    snapshots sized for human Applies; four automated switches a day would evict
    a user's real history in under three days. History and rotation config are
    different things with different lifecycles.
  - **Ride Night Light's schedule rather than adding a second clock.** GNOME
    already computes real sunset/sunrise from cached coordinates. Worth knowing
    that Night Light warms the display and flattens blues, so an evening preset
    that also warms will be double-counted.
  - Slots come from picking 2–4 presets outright (no failure mode, ship first),
    or from inverting one preset — which means flipping lightness in a
    perceptual space while holding hue and chroma, not inverting RGB channels.

  Open: whether the cycle crosses light/dark at all, whether a manual Apply
  pauses it, and whether it rides Night Light's clock or keeps its own.
- [x] Live preview — a schematic window in the Colors tab, redrawn on every
      edit, marking any pair below WCAG AA. Drawn rather than built from real
      widgets because libadwaita only reads named-colour overrides from the
      stylesheet loaded at startup; a CSS provider added at runtime does not
      restyle them, so real widgets would show the launch-time theme
- [ ] Preview with real widgets — would need rendering in a separate process
      that starts with the generated stylesheet already in place
- [ ] Generate a preset from a single color
- [ ] Textures (carbon fibre, gloss, and more)
- [ ] Redesigned splash / welcome page
- [ ] Further visual enhancements beyond the original scope

### Appearance control center

Own the whole *appearance* surface, so GNOME Tweaks isn't needed to manage how
the desktop looks. Most of these are `gsettings` selectors on
`org.gnome.desktop.interface` — a schema Vivid already reads and writes (it
sets `gtk-theme` on apply) — so it's largely UI over plumbing that exists. Pairs
with the external-theme importer above: install a theme **and** switch to it from
one app. Scope stays on *looks* — not the fonts-scaling / startup-apps / keyboard
parts of Tweaks.

- [ ] GTK 3 / legacy theme picker (`interface.gtk-theme`)
- [ ] Icon theme picker (`interface.icon-theme`)
- [ ] Cursor theme + size picker (`interface.cursor-theme`)
- [ ] Light / dark toggle (`interface.color-scheme`)
- [ ] Window control button layout (`wm.preferences.button-layout`)
- [ ] Toggle animations (`interface.enable-animations`)
- [ ] Activate a generated GNOME Shell theme (`shell.extensions.user-theme`, when
      the User Themes extension is present)

### Environment checks — tell the user what's missing

A preset can be correct and still land on an inconsistent desktop, because
`gtk.css` is applied *on top of* whatever base theme resolves underneath — and
host applications and Flatpak applications resolve that base separately. The
same preset then renders two ways depending only on how an app was packaged.

The decision here is deliberate: **report, don't install.** Vivid has the
permissions to install things on the user's behalf and shouldn't. Say what is
missing and what command fixes it, the way the missing-User-Themes-extension
dialog already does.

- [ ] Warn when `interface.gtk-theme` names a theme that sandboxed apps can't
      resolve. Flatpaks read `org.gtk.Gtk3theme.<name>` from
      `/usr/share/runtime/share/themes/`, *not* `/usr/share/themes` — so a
      distro-packaged theme with no matching extension leaves every Flatpak
      falling back to stock Adwaita, silently.
- [ ] Warn when the base theme is not colour-parameterised. GTK 3's built-in
      Adwaita is compiled — 36 `@define-color` against 1,230 baked literals — so
      our colours cannot reach it. adw-gtk3 is the inverse (125 defines, 1,189
      named references, using our exact variable names) and is effectively the
      GTK 3 substrate this app is written for.
- [ ] Warn when the User Themes extension is absent or disabled (partly built)
- [ ] A single "is my desktop consistent?" view — host theme, sandbox theme,
      Shell theme and `gtk.css` either agreeing or not

### Theme Engines & Integrations

Extend theming to targets beyond GTK / adw-gtk3. The old yapsy-based plugin
system is **retired** (it was shelved for maintenance and its UI has been
removed); its capabilities are being rebuilt as first-class, built-in **Theme
Engines** — like the current Monet and GNOME Shell engines — rather than
external plugins.

- [x] Monet engine — Material You palette from a wallpaper, with dynamic
      schemes (nine variants: Vibrant, Tonal Spot, Expressive, … ) and a
      selectable contrast level
- [ ] Icon engine — a recoloured "pseudo-Adwaita" icon theme generated per
      preset, so folders stop being blue under a themed desktop. Prototyped in
      `tools/icons-from-preset.py`: 35 icons, 29 blues mapped through a
      luminance curve, inheriting from Adwaita for everything else. What remains
      is the UI and the in-app generate/apply path.
- [x] GNOME Shell engine — rewritten to retheme the stylesheet the installed
      Shell already ships, rather than vendoring GNOME's SCSS per release (the
      approach that capped it at 45). Version-agnostic, and applies to a
      **running** Shell with no logout. Escapes the nine-value accent enum by
      substituting literals for `-st-accent-color`.
  - [ ] Drop the now-dead machinery: `data/shell/templates/{42,43,44,45}`, the
        `data/submodules/gnome-shell` submodule (2.6 MB of vendored SCSS), and
        the `sassc` / `libsass` modules in the three Flatpak manifests. Left for
        a commit that lands alongside a build, since none of it can be verified
        without one.
  - [ ] Follow `interface.color-scheme` and regenerate — a user theme has only
        one `gnome-shell.css`, so light/dark does not switch by itself.
- [ ] Firefox / browser integration (the Flatpak already grants browser access)
- [ ] GDM theming
- [ ] Kvantum / Qt (KvLibadwaita)
- [ ] Retire the remaining mock plugin plumbing (save/apply no-ops in `main.py`)

### Far Future

Bigger ideas still under consideration — not committed.

- [ ] Base16 / Tinted Theming importer — read machine-readable palette specs
      ([tinted-theming/schemes](https://github.com/tinted-theming/schemes)) to
      auto-generate presets and replace the hand-derived palette ramps with
      canonical spec values

### References

Useful when working on the UI modernization:

- [GNOME Human Interface Guidelines](https://developer.gnome.org/hig/) — layout, spacing, and widget-choice patterns
- [Libadwaita documentation](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/) — see `ToolbarView`, `Breakpoint`, and the row widgets
- [Adwaita Demo](https://flathub.org/apps/org.gnome.Adwaita1.Demo) — interactive gallery of every widget
- [Workbench](https://flathub.org/apps/re.sonny.Workbench) — live GTK4 / Adwaita / Blueprint playground
