## Roadmap

If you'd like to see a new feature, open an issue or submit a PR.

### Immediate Goals

- [x] Working Flatpak targeting GNOME 48+ / runtime 50 (latest)
- [x] Automatically track new GNOME runtime releases
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
- [x] Curated built-in themes — Catppuccin (Mocha/Latte), Gruvbox, Nord, Dracula, Tokyo Night
- [ ] Show user presets in the gallery (built-in schemes done)
- [ ] Color wheel for picking colors
- [ ] Import GTK 3/4 themes from external sources (OpenDesktop, GitHub, and others)
- [ ] Light/dark preset pairs **(high priority)**
- [ ] Day-to-night gradient automation
- [ ] Full theme preview
- [ ] Generate a preset from a single color
- [ ] Textures (carbon fibre, gloss, and more)
- [ ] Redesigned splash / welcome page
- [ ] Further visual enhancements beyond the original scope

### Theme Engines & Integrations

Extend theming to targets beyond GTK / adw-gtk3. The old yapsy-based plugin
system is **retired** (it was shelved for maintenance and its UI has been
removed); its capabilities are being rebuilt as first-class, built-in **Theme
Engines** — like the current Monet and GNOME Shell engines — rather than
external plugins.

- [x] Monet engine (Material 3 palette from a wallpaper)
- [x] GNOME Shell engine
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
