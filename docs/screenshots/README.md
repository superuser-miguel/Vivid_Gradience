# Screenshots

One directory, three consumers: the top-level `README.md`, the Pages site at
`docs/index.html`, and the AppStream metainfo, which points at the hosted
copies under `https://superuser-miguel.github.io/Vivid_Gradience/screenshots/`.
Keep the filenames stable. A released version's metainfo keeps asking for the
names it shipped with, so a file it names must not be deleted.

- `presets.png`: the Presets gallery. The hero shot on the README and the site.
- `colors.png`: the Colors tab with the Rosé Pine preset loaded.
- `colors-light.png`: the same tab with Buttercream, a light preset.
- `theming.png`: the whole Theming tab, every engine and the Desktop group.
- `advanced.png`: the Advanced tab. Only the metainfo uses it.

## Taking them

GNOME on Wayland lets no outside program capture a window, so the app draws
its own picture when `VG_SHOT` is set. `tools/take-screenshots.sh` runs the
installed Flatpak on a headless compositor, once per picture:

```shell
tools/take-screenshots.sh docs/screenshots
```

No window appears on the desktop and no setting is touched. The pictures show
stock Adwaita, not whatever theme is applied on the machine, and the Firefox
profiles in them are stand-ins made for the purpose, so no real profile name
ends up published.
