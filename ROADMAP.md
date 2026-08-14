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

**Current order of work.** Firefox chrome theming and the in-app icon engine are
next — both are concrete, and neither waits on a decision. The inherited Tweaks
pickers follow. The light/dark pair and the time-of-day cycle are deferred: they
share one unresolved question (is the unit a preset, or a *state*?), and guessing
at it would mean building the wrong storage twice.

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
- [ ] Light/dark preset pairs — **deferred**, needs the state-model conversation
      first (see the cycle notes below; the two share one mechanism)
- [ ] Time-of-day theme cycle — rotate 2–4 presets across the day.
      **Deferred**: a concept in progress, and three questions below are still open

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

Finish these before starting the light/dark pair or the time-of-day cycle. They
are bounded, individually small, and none of them is blocked on a decision that
hasn't been made — which is the opposite of the two large features.

Everything here applies to a running session; `gtk-theme`, `icon-theme`,
`cursor-theme`, `cursor-size` and `color-scheme` were each verified to notify
live-running applications.

- [x] GTK 3 / legacy theme picker (`interface.gtk-theme`) — with the warning
      that made it the valuable one: choosing a theme with no
      `org.gtk.Gtk3theme` extension flags the Flatpak split and names the
      install command. (Apply still sets `gtk-theme` to `adw-gtk3`
      unconditionally — surfacing that in the same warning is follow-up.)
- [x] Icon Engine — the generated icon theme is in the app: a Theming-tab
      group that scores the ramps, generates the theme with attribution, and
      sets `interface.icon-theme` on Apply. Remove resets the key unless the
      user has since selected a different theme. (A general icon *picker* for
      arbitrary installed themes remains future control-centre work.)
- [x] Pointer (`interface.cursor-theme`) — a picker in the Desktop group.
      (`cursor-size` / `locate-pointer` still open; and a cursor cannot be
      recoloured the way icons can — Adwaita's are Xcursor binaries with no
      shipped SVG sources, so recolouring would be a separate project.)
- [x] Light / dark toggle (`interface.color-scheme`) — the Dark Style switch
      in the Desktop group. Distinct from the light/dark *pair* feature.
- [x] Window control button layout (`wm.preferences.button-layout`) — four
      common arrangements in the Desktop group.
- [ ] Toggle animations (`interface.enable-animations`)
- [x] Activate a generated GNOME Shell theme (`shell.extensions.user-theme`) —
      done by the Shell engine

Deliberately out of scope, as above: fonts, scaling, startup applications and
keyboard — the parts of Tweaks that are not about how the desktop *looks*.

### Choose colours by measurement, not by lookup table

**Two requests from testing, and they are the same feature seen from both sides.**
The engine should choose a readable foreground automatically; the colour picker
should show the user the same measured information so they can choose
differently. One body of work, two surfaces.

- [ ] **Foreground text follows its background.** Black on light surfaces, white
      on dark ones — but chosen by measurement, not by eye. There are **14
      foreground variables**, each paired with exactly one background:

      accent · destructive · success · warning · error
      window · view · headerbar · card · dialog · popover · thumbnail
      sidebar · secondary_sidebar

      For each pair, if the foreground does not clear the floor on its own
      background, pick or derive one that does. Note the crossover between
      wanting white and wanting black sits at **luminance 0.179**, not at
      lightness 0.5 — getting that wrong is what made the first attempt at this
      push a mid-dark accent toward white and still fail.

- [x] **Put the preset's own palette in the colour picker.** Built: clicking a
      colour opens the scheme's own shades as labelled swatches, with `Custom…`
      falling through to `Gtk.ColorDialog`. What remains is the contrast-aware
      half described below — marking which swatches actually clear the floor
      against the variable being edited.

      Blocked by the GTK API, so it needs building: `Gtk.ColorDialog` exposes
      only `title`, `modal` and `with-alpha` — there is no way to add swatches.
      `Gtk.ColorChooserWidget.add_palette()` can, but is deprecated in GTK 4.10+
      and should not be adopted now. So: a small `Adw.Dialog` holding the
      scheme's 45 palette shades and 46 variables as labelled swatches, with
      `Gtk.ColorDialog` kept behind a "Custom…" button as the escape hatch.

      Worth more than parity with GTK: because the dialog knows *which* variable
      is being edited, it can mark the swatches that actually clear contrast
      against that variable's background — turning a colour picker into a
      readable-colour picker. This is also most of the palette editor already on
      the list.


The accent-foreground bug is the argument for this. A static table said "the text
on an accent comes from `window_fg_color`", which was wrong for 70 of 76 bundled
presets — and the contrast audit reported all 76 passing, because it scores pairs
as they appear in a *preset* while the Shell composes different pairs from the
same variables. Two self-consistent views of the same data, disagreeing by a
factor of two.

This is the lesson the icon engine already learned and this one did not: **score
the output, not the input.** `tools/icons-from-preset.py` picks a palette ramp by
measuring what the folder actually becomes. The Shell engine substitutes values
and hopes.

- [ ] **Pick foregrounds by contrast, not by name.** Given a background, choose
      whichever candidate actually reads on it, rather than trusting one mapping
      to be right for every scheme. Self-correcting: a preset with a poor
      `accent_fg_color` gets a better one instead of an unreadable toggle.
      (Peach Fizz passes at 4.62 today — correct, but thin.)
- [ ] **Audit the generated stylesheet, not just the preset.** Every engine
      emits its own foreground/background pairings — Shell, GTK, Firefox chrome.
      Scoring the artefact would catch this whole class of bug, including the
      ones not yet found, and would have caught this one immediately.
- [ ] Extend `tools/audit-contrast.py` to cover generated output, and add the
      colour-vision and Night Light simulations while it is being touched.

### Stylesheet ownership — done

- [x] Warn on Apply when `gtk.css` exists without the Vivid header, naming
      its size and offering import-as-theme / back-up-and-replace / cancel.
- [x] "Rescue, don't just back up" — the foreign stylesheet moves into
      `~/.local/share/themes` as a selectable theme instead of dying.
- [x] A Custom Themes group on Advanced manages that library (list, import
      a folder, remove). The GitHub/.zip installer will feed the same group.
- [x] Map the preset accent onto `interface.accent-color` on Apply.

### Environment checks — tell the user what's missing

**Build this mechanism once, generically.** There are now three separate
dependencies that have to be detected and reported, and writing a bespoke dialog
for each is how they drift apart:

| Feature | Needs | Currently |
|---|---|---|
| GTK 3 theming | `adw-gtk3` on the host **and** `org.gtk.Gtk3theme.adw-gtk3` for sandboxed apps | neither checked |
| GNOME Shell | the User Themes extension | partly checked |
| Firefox | `firefox-gnome-theme` in the profile | checked; installable in-app |

In every case the answer is the same shape: say what is missing, say what
installs it, do not install it.

A preset can be correct and still land on an inconsistent desktop, because
`gtk.css` is applied *on top of* whatever base theme resolves underneath — and
host applications and Flatpak applications resolve that base separately. The
same preset then renders two ways depending only on how an app was packaged.

The decision here is deliberate: **report, don't install.** Vivid has the
permissions to install things on the user's behalf and shouldn't. Say what is
missing and what command fixes it, the way the missing-User-Themes-extension
dialog already does.

One deliberate exception (2026-07-31): **firefox-gnome-theme**. It is not a
system component — it is plain files inside the user's Firefox profile, a
directory the Firefox engine already writes to. The app offers to install a
*pinned, tested* release (never latest; the pin moves at our release cadence)
into the profiles that lack it, stamps every install it makes, and can
uninstall exactly those installs again — theme tree, `@import` lines and
`user.js` prefs block. A copy the user installed themselves carries no stamp
and is never updated, uninstalled or otherwise touched. The rule stands for
everything system-level: the User Themes extension and the Gtk3theme Flatpak
remain report-only.

- [x] Warn when `interface.gtk-theme` names a theme that sandboxed apps can't
      resolve. Flatpaks read `org.gtk.Gtk3theme.<name>` from
      `/usr/share/runtime/share/themes/`, *not* `/usr/share/themes` — so a
      distro-packaged theme with no matching extension leaves every Flatpak
      falling back to stock Adwaita, silently. Shipped with the Desktop group:
      the GTK3 theme picker checks for the extension via the host's
      `flatpak list` and warns only on a confirmed miss.
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
- [x] Icon engine — a recoloured "pseudo-Adwaita" icon theme generated per
      preset, so folders stop being blue under a themed desktop. 35 icons, 29
      blues mapped through a luminance curve, ramp chosen by measured visibility
      against the view background, inheriting from Adwaita for everything else.
      Now an in-app engine (`backend/theming/icons.py`) with generate, apply and
      remove; `tools/icons-from-preset.py` remains the scriptable form and the
      two are kept in sync.
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
- [x] Firefox / browser integration — a built-in Firefox Engine on the Theming
      tab, ported from the retired yapsy plugin. Walks `profiles.ini` for
      Firefox, LibreWolf and Waterfox (host, Flatpak and Snap) and writes the
      preset's `--gnome-*` variables into
      `<profile>/chrome/firefox-gnome-theme/customChrome.css`.

      Fixed while porting rather than carried over:
  - [x] **The dark-theme assumption.** Tab backgrounds were hardcoded white
        overlays, invisible on a light preset; they now derive from the
        preset's own foreground, so they darken light schemes and lighten dark
        ones.
  - [x] **The `about:newtab` block ignored the preset entirely** — Firefox's
        stock dark palette was written as literals. It now derives from the
        same preset roles as everything else.
  - [x] Depends on
        [firefox-gnome-theme](https://github.com/rafaelmardojai/firefox-gnome-theme)
        being installed in the profile; the `--gnome-*` variables are its API.
        Detected — and since 2026-07-31 installable from inside the app (the
        sanctioned exception to report-don't-install above): a pinned release,
        stamp-guarded, fully uninstallable, with the user's own installs never
        touched.
  - [x] Also fixed in the port: `IsRelative` was compared as an integer against
        a string, so absolute-path profiles never resolved; and a
        `customChrome.css` we did not write is skipped, not overwritten —
        firefox-gnome-theme documents it as the *user's* customisation hook.
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
