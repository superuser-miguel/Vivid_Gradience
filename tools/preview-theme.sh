#!/usr/bin/env bash
# Preview a preset on real widgets without touching your desktop.
#
# Applying a preset rewrites ~/.config/gtk-{3.0,4.0}/gtk.css, and libadwaita
# only reads that file at startup — so seeing a theme normally means restarting
# every app, which in practice means logging out and losing your workspaces.
#
# This sidesteps both. It writes the preset into a throwaway XDG_CONFIG_HOME and
# launches a demo app pointed at it. Real GTK, real libadwaita, real widgets —
# and your actual config is never touched, so there is nothing to revert.
#
# Usage:
#   tools/preview-theme.sh rot
#   tools/preview-theme.sh data/presets/eminence.json
#   tools/preview-theme.sh rot --app widget-factory
#
# Apps:
#   adwaita   libadwaita's own demo, host binary (default)
#   widget-factory   gtk4-widget-factory from the GNOME 50 SDK — denser, shows
#                    more widget states at once
set -euo pipefail

APP=adwaita
ARG=${1:-}
[ -n "$ARG" ] || { sed -n '3,20p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
shift || true
while [ $# -gt 0 ]; do
    case "$1" in
        --app) APP=${2:?--app needs a value}; shift 2 ;;
        *) echo "unknown option: $1" >&2; exit 1 ;;
    esac
done

# Resolve a bare name to a bundled preset.
if [ -f "$ARG" ]; then
    PRESET=$ARG
else
    PRESET="data/presets/${ARG}.json"
    [ -f "$PRESET" ] || { echo "no such preset: $ARG (tried $PRESET)" >&2; exit 1; }
fi

CFG=$(mktemp -d -t vivid-preview-XXXXXX)
trap 'rm -rf "$CFG"' EXIT
mkdir -p "$CFG/gtk-4.0" "$CFG/gtk-3.0"

python3 - "$PRESET" "$CFG" <<'PY'
import json, sys, os
preset, cfg = sys.argv[1], sys.argv[2]
d = json.load(open(preset))
css = "".join(f"@define-color {k} {v};\n" for k, v in d["variables"].items())
for prefix, shades in d.get("palette", {}).items():
    css += "".join(f"@define-color {prefix}{k} {v};\n" for k, v in shades.items())
for sub in ("gtk-4.0", "gtk-3.0"):
    open(os.path.join(cfg, sub, "gtk.css"), "w").write(css)
print(f"  {d.get('name', preset)} — {len(d['variables'])} variables")
PY

echo "  config: $CFG  (removed on exit)"

case "$APP" in
    adwaita)
        command -v adwaita-1-demo >/dev/null \
            || { echo "adwaita-1-demo not installed" >&2; exit 1; }
        XDG_CONFIG_HOME="$CFG" adwaita-1-demo
        ;;
    widget-factory)
        # Shipped by the SDK rather than installed on the host. --filesystem is
        # needed because the temp config lives outside the sandbox's defaults.
        XDG_CONFIG_HOME="$CFG" flatpak run \
            --command=gtk4-widget-factory \
            --filesystem="$CFG" \
            --env=XDG_CONFIG_HOME="$CFG" \
            org.gnome.Sdk//50
        ;;
    *)
        echo "unknown app: $APP (want 'adwaita' or 'widget-factory')" >&2
        exit 1
        ;;
esac
