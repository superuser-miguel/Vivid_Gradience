# Fork Cleanup TODO

Changes needed to replace upstream (`GradienceTeam/Gradience`) identity with your
own. Work through each section before publishing.

Note: the original rebrand sweep replaced the string `Gradience` with
`superuser-miguel` indiscriminately, so several "wrong owner" bugs below are that
sweep overshooting — including in this file's own header, fixed 2026-08-14.

---

## 1. Identity / Authorship — ✅ DONE (2026-08-14)

- [x] `gradience.doap`
  - `<name>` and the description now say `Vivid Gradience`
  - Maintainer email moved to the GitHub noreply address already used for
    commits (`16271056+superuser-miguel@users.noreply.github.com`), rather than
    upstream's `ng.eric@ik.me`

- [x] `gradience/frontend/views/about_dialog.py`
  - `developer_name` and `developers` are correct as-is — that really is the
    fork's developer.
  - `copyright` was claiming `© 2022-2026 superuser-miguel`, i.e. upstream's
    years under the fork's name. Now credits both, matching the per-file header
    convention already used in the tree (`Gradience Team` for inherited files,
    `Vivid Gradience contributors` for new ones).

- [x] `.github/CODEOWNERS`
  - Was `@GradienceTeam/Core` plus a bare `superuser-miguel` and no path
    pattern, which is not valid CODEOWNERS syntax — the file did nothing.
    Now `* @superuser-miguel`.

- [x] `MAINTAINERS.md`
  - The History line claimed the project was "previously maintained as
    Gradience" by @superuser-miguel, linking to this repo. Both halves were the
    sweep's doing; it now names the Gradience Team and links
    `GradienceTeam/Gradience`.

---

## 2. App ID / Namespace — ✅ DONE

App-id renamed to the valid RDNN `io.github.superuser_miguel.VividGradience`
(the old `com.github.superuser-miguel.VividGradience` was invalid for Flatpak:
hyphens are only allowed in the last segment). GitHub URLs keep the real
hyphenated `superuser-miguel` account — only the app-id/resource paths changed.

- [x] `meson.build` — `PROJECT_RDNN_NAME`
- [x] Renamed + updated `data/io.github.superuser_miguel.VividGradience.*`
  - `*.appdata.xml.in.in`
  - `*.desktop.in.in`
  - `*.gschema.xml.in` — GSettings path `/io/github/superuser_miguel/Vivid_Gradience/`
- [x] `data/gradience.gresource.xml` — resource prefix `/io/github/superuser_miguel/Vivid_Gradience`
- [x] `gradience/backend/constants.py.in` — `rootdir`
- [x] Renamed + updated `build-aux/flatpak/io.github.superuser_miguel.VividGradience*.json`
- [x] Renamed icon files (were still `com.github.hydroxycarbamide.Gradience.*` from upstream)
- [x] Updated `.github/workflows/{build,repo}.yml` manifest paths + `po/POTFILES`

---

## 3. Screenshots (appdata)

- [ ] `data/com.github.superuser-miguel.VividGradience.appdata.xml.in.in`
  - All 5 `<image>` URLs point to `GradienceTeam/Design` on GitHub
  - Replace with your own screenshots, or remove the `<screenshots>` block

---

## 4. Release History (appdata)

- [ ] Same `appdata.xml.in.in` — the `<releases>` block lists the full upstream
  Gradience changelog (0.1.0 through 0.8.0-beta4)
  - Clear it and add your own first release entry

---

## 5. Contact / URLs

- [ ] `SECURITY.md` — vulnerability reporting URL still has `superuser-miguel/Vivid_Gradience`
- [ ] `HACKING.md` — clone URL still points to `superuser-miguel/Vivid_Gradience`

---

## 6. License / Copyright Headers

- The `LICENSE` file is GPL-3.0 — keep it as-is (required by the license)
- Source file headers say `Copyright (C) 2022 Gradience Team`
  - **Add** your own line (e.g. `Copyright (C) 2026 Your Name`) rather than
    replacing the existing ones — GPL forks accumulate copyright holders
