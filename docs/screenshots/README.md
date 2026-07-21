# Screenshots

One directory, three consumers — the top-level `README.md`, the Pages site at
`docs/index.html`, and (eventually) the AppStream metainfo. Keep the filenames
stable so nothing has to be re-pointed.

- `presets.png` — the Presets gallery. The hero shot, used at the top of both
  the README and the site.
- `colors.png` — the Colors editor, with the search field and collapsible
  categories visible.
- `theming.png` — the Theming tab, showing the Shell and Monet engine groups.
- `advanced.png` — the Advanced tab and its custom CSS editor.
- `preferences.png` — the Preferences dialog.

Tips:

- Use a consistent window size and a clean desktop background across the set.
- HiDPI (2×) captures look crisp on GitHub; keep widths reasonable (~1400px).
- The AppStream `<screenshots>` block needs **hosted URLs**, not repo paths.
  Once Pages is serving this directory, those URLs are
  `https://superuser-miguel.github.io/Vivid_Gradience/screenshots/<name>.png`.
  Note that `meson` validates the metainfo with `--no-net`, so the URLs are not
  fetched at build time.
