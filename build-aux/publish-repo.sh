#!/usr/bin/env bash
# Publish Vivid Gradience to its signed, auto-updating Flatpak repo.
#
# Vivid Gradience ships two ways: a one-off .flatpak bundle on GitHub Releases,
# and this hosted OSTree repo at https://superuser-miguel.github.io/Vivid_Gradience-repo/
# that `flatpak update` tracks. This script (re)builds the hosted repo and pushes it.
#
# Layout choice (deliberate, matches Septima): the published repo is regenerated
# wholesale and **force-pushed as a single commit** each release, so its git
# history never accumulates superseded, content-addressed OSTree objects. It is a
# separate GitHub repo from the code — the code repo stays clean.
#
# Everything heavy (build dir, state dir, OSTree repo) is kept on a tmpfs under
# $TMPDIR so it never touches $HOME, which runs tight on free space.
#
# Prerequisites:
#   - flatpak-builder, ostree, git, gpg
#   - the signing secret key present in the local GPG keyring (see KEYID below);
#     losing it means you can no longer publish trusted updates to this remote.
#   - push access to git@github.com:superuser-miguel/Vivid_Gradience-repo.git
#   - the release TAG the manifest is pinned to must already be pushed (the build
#     fetches the source over the network).
#
# Usage:  build-aux/publish-repo.sh
set -euo pipefail

KEYID="D67DB8E03D50A8C0"          # signs the tags too; public key is baked into the .flatpakref
APP_ID="io.github.superuser_miguel.VividGradience"
PAGES_URL="https://superuser-miguel.github.io/Vivid_Gradience-repo"
PUBLISH_REMOTE="git@github.com:superuser-miguel/Vivid_Gradience-repo.git"
MANIFEST="build-aux/flatpak/${APP_ID}.release.json"

here="$(cd "$(dirname "$0")/.." && pwd)"
cd "$here"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
repo="$work/repo"
build="$work/build-dir"
state="$work/state"

echo ">> Building release (unsigned) into a fresh OSTree repo (all on tmpfs)…"
# Build unsigned first: the build takes minutes, and signing during it would
# hold the gpg passphrase open the whole time (the agent cache expires and the
# commit signature fails with "Pinentry: Timeout"). Sign in the quick step below
# instead, so pinentry is needed for only a few seconds.
flatpak-builder --user --force-clean --state-dir="$state" --repo="$repo" \
    "$build" "$MANIFEST"

echo ">> Signing every ref + the summary (pinentry prompts once if the key is locked)…"
ostree --repo="$repo" refs | while read -r ref; do
    ostree --repo="$repo" gpg-sign "$ref" "$KEYID" >/dev/null
done
flatpak build-update-repo --generate-static-deltas --prune --gpg-sign="$KEYID" "$repo"

echo ">> Assembling the publish tree (repo + .flatpakref + landing page)…"
pub="$work/publish"
mkdir -p "$pub"
cp -a "$repo" "$pub/repo"
touch "$pub/.nojekyll"   # serve OSTree byte-for-byte; do not let Jekyll rewrite it

key_b64="$(gpg --export "$KEYID" | base64 --wrap=0)"
cat > "$pub/VividGradience.flatpakref" <<EOF
[Flatpak Ref]
Name=${APP_ID}
Branch=master
Url=${PAGES_URL}/repo/
Title=Vivid Gradience — change the look of Adwaita
Homepage=https://superuser-miguel.github.io/Vivid_Gradience/
Comment=Signed Flatpak repo for automatic updates
GPGKey=${key_b64}
RuntimeRepo=https://flathub.org/repo/flathub.flatpakrepo
IsRuntime=false
EOF

cat > "$pub/index.html" <<'EOF'
<!doctype html><meta charset=utf-8><title>Vivid Gradience — Flatpak repo</title>
<style>body{font-family:system-ui,sans-serif;max-width:40rem;margin:4rem auto;padding:0 1rem;line-height:1.6}code{background:#f0f0f0;padding:.1em .3em;border-radius:3px}</style>
<h1>Vivid Gradience — signed Flatpak repo</h1>
<p>Automatic updates for <a href="https://superuser-miguel.github.io/Vivid_Gradience/">Vivid Gradience</a>, the Adwaita theme customizer.</p>
<pre><code>flatpak install --user https://superuser-miguel.github.io/Vivid_Gradience-repo/VividGradience.flatpakref
flatpak run io.github.superuser_miguel.VividGradience</code></pre>
<p>Updates then arrive with <code>flatpak update</code>. Signed with the project's GPG key.</p>
EOF

echo ">> Force-pushing as a single squashed commit…"
version="$(date +%Y-%m-%d)"
git -C "$pub" init -q -b main
git -C "$pub" add -A
git -C "$pub" -c user.name=superuser-miguel \
    -c user.email=16271056+superuser-miguel@users.noreply.github.com \
    commit -q -m "Publish Vivid Gradience (${version}) — signed OSTree repo + .flatpakref"
git -C "$pub" remote add origin "$PUBLISH_REMOTE"
git -C "$pub" push -u --force origin main

echo ">> Done. Verify from the public URL:"
echo "   flatpak install --user ${PAGES_URL}/VividGradience.flatpakref"
