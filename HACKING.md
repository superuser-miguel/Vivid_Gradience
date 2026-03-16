## 🙌 Contribute to Vivid Gradience

### Code

Fork this repository, then open a pull request when you're done adding features
or fixing bugs. Please open an issue first for significant changes so we can
discuss the approach.

### Localization

Localization is not actively maintained at this time. If you're interested in
helping, open an issue and we can discuss setting up a translation platform.

## 🏗️ Building from Source

### GNOME Builder (Recommended)

GNOME Builder is the primary development environment for this application.
It uses Flatpak manifests to create a consistent build environment cross-distro.

1. Download [GNOME Builder](https://flathub.org/apps/details/org.gnome.Builder)
2. Click "Clone Repository" and use `https://github.com/superuser-miguel/Vivid_Gradience.git`
3. Click the build button at the top once the project is loaded

### Flatpak Builder

Use this method if you prefer the command line or have issues with GNOME Builder.

#### Prerequisites

- `flatpak-builder`
- GNOME SDK and Platform runtime 49
```shell
flatpak install org.gnome.Sdk//49 org.gnome.Platform//49
```

#### User installation
```shell
git clone https://github.com/superuser-miguel/Vivid_Gradience.git
cd Vivid_Gradience
flatpak-builder --install --user --force-clean repo/ \
  build-aux/flatpak/com.github.superuser-miguel.VividGradience.json
```

#### System installation
```shell
git clone https://github.com/superuser-miguel/Vivid_Gradience.git
cd Vivid_Gradience
flatpak-builder --install --system --force-clean repo/ \
  build-aux/flatpak/com.github.superuser-miguel.VividGradience.json
```

#### Devel build (nightly runtime)
```shell
flatpak remote-add --if-not-exists gnome-nightly \
  https://nightly.gnome.org/gnome-nightly.flatpakrepo
flatpak install gnome-nightly org.gnome.Sdk//master org.gnome.Platform//master

flatpak-builder --install --user --force-clean repo/ \
  build-aux/flatpak/com.github.superuser-miguel.VividGradience.Devel.json
```

### Meson (Local build)

Use this for fast iteration without the Flatpak layer.

#### Prerequisites

- Python 3
- PyGObject `python-gobject`
- Blueprint compiler [`blueprint-compiler`](https://jwestman.pages.gitlab.gnome.org/blueprint-compiler/setup.html)
- GTK4 `gtk4`
- Libadwaita >= 1.4 `libadwaita`
- Meson `meson`
- Ninja `ninja-build`
```shell
sudo dnf install meson ninja-build python3-gobject gtk4 libadwaita \
  blueprint-compiler
pip install -r requirements.txt
```

#### Local build (development)
```shell
git clone https://github.com/superuser-miguel/Vivid_Gradience.git
cd Vivid_Gradience
meson setup builddir
meson configure builddir -Dprefix="$(pwd)/builddir"
ninja -C builddir install
ninja -C builddir run
```

> **Note**
> Use the `local.sh` script for quick rebuilds during development.
