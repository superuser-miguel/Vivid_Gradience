# Fork Cleanup TODO

Changes needed to replace upstream (`superuser-miguel/Vivid_Gradience`) identity
with your own. Work through each section before publishing.

---

## 1. Identity / Authorship

- [ ] `gradience.doap`
  - Change `<name>Gradience</name>` → `Vivid Gradience`
  - Update/replace the `ng.eric@ik.me` email if it is not yours

- [ ] `gradience/frontend/views/about_dialog.py`
  - Replace `superuser-miguel` in `developer_name`, `developers` list, and `copyright`

- [ ] `.github/CODEOWNERS`
  - Remove `@GradienceTeam/Core`
  - Replace `superuser-miguel` with your GitHub username

- [ ] `MAINTAINERS.md`
  - Fix "Previously maintained as" link — it currently points to
    `superuser-miguel/Vivid_Gradience` but should point to
    `https://github.com/GradienceTeam/Gradience` (the actual upstream)

---

## 2. App ID / Namespace

Only needed if you are publishing under a different identity (e.g. Flathub).
The RDNN `com.github.superuser-miguel.VividGradience` cascades through:

- [ ] `meson.build` — `PROJECT_RDNN_NAME`
- [ ] Rename + update contents of `data/com.github.superuser-miguel.VividGradience.*`
  - `*.appdata.xml.in.in`
  - `*.desktop.in.in`
  - `*.gschema.xml.in` — GSettings path `/com/github/superuser-miguel/Vivid_Gradience/`
- [ ] `data/gradience.gresource.xml` — resource prefix `/com/github/superuser-miguel/Vivid_Gradience`
- [ ] `gradience/backend/constants.py.in` — `rootdir`
- [ ] Rename + update `build-aux/flatpak/com.github.superuser-miguel.VividGradience*.json`

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
