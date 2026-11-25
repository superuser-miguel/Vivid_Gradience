#!/usr/bin/bash
# Take the documentation screenshots from the installed Flatpak.
#
#   tools/take-screenshots.sh OUTDIR [name:page:WxH[:preset[:scheme]] ...]
#
# GNOME on Wayland lets no outside program capture a window, so the app draws
# its own picture when VG_SHOT is set (see _dev_screenshot in
# gradience/frontend/main.py). Each picture is one run of the app on a
# headless compositor: nothing appears on the desktop, settings live in
# memory, and the applied theme is hidden so the pictures show stock Adwaita.
#
# The Firefox profiles are stand-ins in a throwaway home directory, so no real
# profile name is published. The first one carries the cached theme release,
# if there is one, so the engine shows an installed state.
set -u

APP=io.github.superuser_miguel.VividGradience
[ $# -ge 1 ] || { echo "usage: $0 OUTDIR [name:page:WxH[:preset[:scheme]] ...]" >&2; exit 2; }
OUT=$(realpath "$1"); shift
mkdir -p "$OUT"
[ $# -gt 0 ] || set -- \
    presets:presets:1280x900 \
    colors:colors:1280x900:rose-pine \
    colors-light:colors:1280x900:buttercream:default \
    theming:theming:1280x2170 \
    advanced:plugins:1280x900

# Short paths: a Wayland socket path has a length limit.
WORK=$(mktemp -d -p "${TMPDIR:-/tmp}" vgshot.XXXX)
export XDG_RUNTIME_DIR="$WORK/rt"; mkdir -m 700 "$XDG_RUNTIME_DIR"
HOME_DIR="$WORK/home"
FF="$HOME_DIR/.mozilla/firefox"
mkdir -p "$FF/ab12cd34.default-release/chrome" "$FF/ef56gh78.Work" \
         "$HOME_DIR/.librewolf/ij90kl12.default"
printf '[Profile0]\nName=default-release\nIsRelative=1\nPath=ab12cd34.default-release\nDefault=1\n\n[Profile1]\nName=Work\nIsRelative=1\nPath=ef56gh78.Work\n' > "$FF/profiles.ini"
printf '[Profile0]\nName=default\nIsRelative=1\nPath=ij90kl12.default\n' > "$HOME_DIR/.librewolf/profiles.ini"
CACHE=$(ls -d "$HOME"/.cache/gradience/firefox-gnome-theme/v* 2>/dev/null | sort -V | tail -1)
if [ -n "$CACHE" ]; then
    C="$FF/ab12cd34.default-release/chrome"
    cp -r "$CACHE" "$C/firefox-gnome-theme"
    printf '%s\nInstalled by Vivid Gradience from\nhttps://github.com/rafaelmardojai/firefox-gnome-theme\n' \
        "$(basename "$CACHE")" > "$C/firefox-gnome-theme/.vivid-gradience-managed"
    printf '@import "firefox-gnome-theme/userChrome.css";\n' > "$C/userChrome.css"
    printf '@import "firefox-gnome-theme/userContent.css";\n' > "$C/userContent.css"
fi

cleanup() {
    fusermount -u "$XDG_RUNTIME_DIR/doc" 2>/dev/null
    fusermount -u "$XDG_RUNTIME_DIR/gvfs" 2>/dev/null
    rm -rf "$WORK"
}
trap cleanup EXIT

export APP OUT HOME_DIR SHOTS="$*"
timeout 600 dbus-run-session -- bash -c '
mutter --headless --no-x11 --wayland-display=vgshot --virtual-monitor 2200x3600 >/dev/null 2>&1 &
M=$!
for i in $(seq 100); do [ -S "$XDG_RUNTIME_DIR/vgshot" ] && break; sleep 0.1; done
status=0
for spec in $SHOTS; do
    IFS=: read -r name page size preset scheme <<<"$spec"
    rm -f "$OUT/$name.png"
    WAYLAND_DISPLAY=vgshot timeout 60 flatpak run \
        --filesystem="$OUT" --filesystem="$HOME_DIR" --nofilesystem=xdg-config/gtk-4.0 \
        --env=HOME="$HOME_DIR" --env=GDK_BACKEND=wayland --env=GTK_A11Y=none \
        --env=GSETTINGS_BACKEND=memory \
        --env=ADW_DEBUG_COLOR_SCHEME="${scheme:-prefer-dark}" \
        --env=VG_SHOT="$OUT/$name.png" --env=VG_PAGE="$page" --env=VG_SIZE="$size" \
        ${preset:+--env=VG_PRESET="$preset"} "$APP" >/dev/null 2>&1
    if [ -f "$OUT/$name.png" ]; then echo "ok       $name"; else echo "MISSING  $name"; status=1; fi
done
kill $M
exit $status' 2>/dev/null | grep -E "^(ok|MISSING)"
exit "${PIPESTATUS[0]}"
