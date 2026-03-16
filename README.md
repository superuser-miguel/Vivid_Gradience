<h1 align="center">
  <img src="data/icons/hicolor/scalable/apps/com.github.superuser-miguel.VividGradience.svg" alt="Vivid Gradience" width="192" height="192"/>
  <br>
  Vivid Gradience
</h1>

<p align="center">
  <strong>Change the look of Adwaita, with ease — built for modern GNOME</strong>
</p>

<br>

<p align="center">
  <a href="https://github.com/superuser-miguel/Vivid_Gradience/actions/workflows/build.yml">
    <img alt="Build status" src="https://github.com/superuser-miguel/Vivid_Gradience/actions/workflows/build.yml/badge.svg"/>
  </a>
</p>

> Vivid Gradience is a fork of [Gradience](https://github.com/GradienceTeam/Gradience),
> by way of [hydroxycarbamide's fork](https://github.com/hydroxycarbamide/Gradience).
> The original project was archived in June 2024.
>
> **Goals of this fork:**
> - 🔧 Working, maintained compatibility with GNOME 48+
> - 🎨 Future visual enhancements beyond the original scope
> - 📦 An up-to-date Flatpak targeting current GNOME runtimes

---

Vivid Gradience is a tool for customizing Libadwaita applications and the adw-gtk3 theme.

## ✨ Features

- 🎨 Change any color of the Adwaita theme
- 🖼️ Apply a Material 3 color scheme from your wallpaper
- 🎁 Use and share presets with other users
- ⚙️ Advanced customization with CSS

## 🎨 Theming Setup

### Libadwaita applications

No additional setup is required for native Libadwaita applications.

For Flatpak Libadwaita applications, override their permissions:

- Run `sudo flatpak override --filesystem=xdg-config/gtk-4.0` or
- Use [Flatseal](https://github.com/tchx84/Flatseal) and add `xdg-config/gtk-4.0`
  to **Other files** in the **Filesystem** section of **All Applications**

### GTK 3 applications

- Install the [adw-gtk3](https://github.com/lassekongo83/adw-gtk3#readme) theme
- For Flatpak applications, override permissions:
  - Run `sudo flatpak override --filesystem=xdg-config/gtk-3.0` or
  - Use Flatseal as above, with `xdg-config/gtk-3.0`

## 🔄 Reverting Theming

Open **Preferences → Theming → Reset & Restore Presets** and click Reset
for GTK 3 or Libadwaita.

<details>
  <summary>Manual revert</summary>
```shell
