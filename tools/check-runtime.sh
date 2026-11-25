#!/usr/bin/bash
# Is the GNOME runtime the manifests pin still the latest one on Flathub?
#
#   tools/check-runtime.sh
#
# Exit 0 when the pin is current, 1 when a newer runtime is out (or the two
# shipping manifests disagree), 2 when Flathub could not be asked. Moving the
# pin is a release step, done by hand: see RELEASING.md.
set -u
cd "$(dirname "$0")/.."

APP=io.github.superuser_miguel.VividGradience
pin() { grep -oP '"runtime-version"\s*:\s*"\K[0-9]+' "build-aux/flatpak/$1"; }

dev=$(pin "$APP.json")
rel=$(pin "$APP.release.json")
ci=$(grep -ohP 'flatpak-github-actions:gnome-\K[0-9]+' .github/workflows/*.yml | sort -u | tr '\n' ' ')
# Flathub may be set up per user, system-wide or both, and flatpak asks which
# when it is both, so each is tried by name.
latest=""
for where in --user --system; do
    latest=$(flatpak remote-ls $where flathub --runtime --all --columns=ref </dev/null 2>/dev/null \
        | grep -oP '^runtime/org\.gnome\.Platform/x86_64/\K[0-9]+$' | sort -n | tail -1)
    [ -n "$latest" ] && break
done

echo "manifest:          $dev"
echo "release manifest:  $rel"
echo "CI container:      ${ci:-none}"
echo "latest on Flathub: ${latest:-unknown}"

[ -n "$latest" ] || { echo "Could not read the runtime list from Flathub." >&2; exit 2; }
status=0
[ "$dev" = "$rel" ] || { echo "The two manifests disagree."; status=1; }
for v in $ci; do [ "$v" = "$dev" ] || { echo "A CI container is on $v, the manifest on $dev."; status=1; }; done
if [ "$dev" -lt "$latest" ]; then
    echo "A newer runtime is out: $dev -> $latest."
    status=1
fi
[ $status -eq 0 ] && echo "The pin is current."
exit $status
