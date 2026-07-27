# Releasing

Vivid Gradience ships as a single-file `.flatpak` bundle attached to a GitHub
Release, alongside the GitHub Pages site. **Not Flathub** — see the note at the
bottom.

There are two Flatpak manifests, and the difference matters:

| Manifest | Source | Use |
| --- | --- | --- |
| `io.github.superuser_miguel.VividGradience.json` | `dir` — the working tree | Local builds while developing |
| `io.github.superuser_miguel.VividGradience.release.json` | `git` — pinned tag **and** commit | Releases only |

The release manifest is pinned so a published bundle can be rebuilt exactly from
its tag, months later, regardless of what the working tree looks like. That
guarantee only holds if the pin is updated — hence step 4.

## Steps

**1. Bump the version.** `meson.build` `version:` and the `<release>` entry in
`data/io.github.superuser_miguel.VividGradience.appdata.xml.in.in` must agree.
Use the real date; `type="stable"` unless it genuinely is a pre-release.

**2. Commit and tag — both GPG-signed.** Releases are signed with the
`superuser-miguel (git_keys)` key `D67DB8E03D50A8C0` (it matches the repo's
commit identity; signing is non-interactive here). Note `-u` is a `git tag`
flag — for the commit use `--gpg-sign=`.

```shell
git commit -a --gpg-sign=D67DB8E03D50A8C0 -m "Release vX.Y.Z"
git tag -u D67DB8E03D50A8C0 -m "Vivid Gradience vX.Y.Z" vX.Y.Z
git push origin main --tags
```

The tag must be pushed *before* the next step — the release build fetches the
source over the network, so an unpushed tag cannot be resolved.

**3. Note the commit the tag points at.**

```shell
git rev-parse vX.Y.Z^{commit}
```

The `^{commit}` suffix matters. These are annotated tags, so a bare
`git rev-parse vX.Y.Z` returns the *tag object's* id, not the commit — and
flatpak-builder cannot check that out.

**4. Update the pin** in `build-aux/flatpak/…VividGradience.release.json` —
both `tag` and `commit`:

```shell
python3 - <<'EOF'
import json, collections, subprocess
TAG = "vX.Y.Z"
p = "build-aux/flatpak/io.github.superuser_miguel.VividGradience.release.json"
m = json.load(open(p), object_pairs_hook=collections.OrderedDict)
s = m["modules"][-1]["sources"][0]
s["tag"] = TAG
s["commit"] = subprocess.check_output(["git", "rev-parse", TAG + "^{commit}"]).decode().strip()
json.dump(m, open(p, "w"), indent=4); open(p, "a").write("\n")
print("pinned", TAG, "->", s["commit"])
EOF
```

Commit that pin update too — a release whose manifest still points at the
previous tag is the failure this whole file exists to prevent.

**5. Build and bundle.**

```shell
flatpak-builder --user --force-clean --repo=repo-release build-dir-release \
  build-aux/flatpak/io.github.superuser_miguel.VividGradience.release.json

flatpak build-bundle repo-release VividGradience.flatpak \
  io.github.superuser_miguel.VividGradience \
  --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo
```

If `$HOME` is near full, the ostree export fails with `min-free-space-percent
'3%' would be exceeded`. Build on another filesystem instead — point the state
dir, build dir and repo at a roomier mount (the `/tmp` tmpfs works, and keeping
all three together also satisfies the "same filesystem" requirement):

```shell
S=/tmp/rel; flatpak-builder --user --force-clean \
  --state-dir=$S/fb-state --repo=$S/repo $S/build-dir \
  build-aux/flatpak/io.github.superuser_miguel.VividGradience.release.json
flatpak build-bundle $S/repo VividGradience.flatpak \
  io.github.superuser_miguel.VividGradience \
  --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo
```

Confirm the bundle really came from the tag before publishing: the built tree
should carry the new `<release>` version in its metainfo and include files that
only exist at that tag (e.g. `backend/theming/backup.py`).

**6. Sign the bundle, then publish.** Detach-sign the bundle and a checksum
file with the same key, and attach all four to the release.

```shell
KEY=D67DB8E03D50A8C0
sha256sum VividGradience.flatpak > SHA256SUMS
gpg --batch --yes --local-user $KEY --detach-sign --armor VividGradience.flatpak
gpg --batch --yes --local-user $KEY --detach-sign --armor SHA256SUMS

gh release create vX.Y.Z \
  VividGradience.flatpak VividGradience.flatpak.asc SHA256SUMS SHA256SUMS.asc \
  --repo superuser-miguel/Vivid_Gradience --verify-tag \
  --title "Vivid Gradience vX.Y.Z" --notes "…"
```

Always pass `--repo superuser-miguel/Vivid_Gradience` — the repo is a GitHub
fork, so `gh` can otherwise resolve to the upstream parent.

`repo-release/`, `build-dir-release/`, `*.flatpak`, `*.asc` and `SHA256SUMS`
are all gitignored — release artifacts are published, never committed.

**7. Update the hosted, auto-updating repo.** The primary install path is the
signed OSTree repo at `superuser-miguel.github.io/Vivid_Gradience-repo` (users
track it with `flatpak update`). After the tag is pushed and the manifest pinned
(steps 2–4), publish it:

```shell
build-aux/publish-repo.sh
```

It rebuilds v-current from the pinned manifest **unsigned**, then signs every
ref + the summary and force-pushes a squashed commit to the separate
`Vivid_Gradience-repo`. Signing is deliberately a quick final step: the key has
a passphrase, and signing *during* the multi-minute build lets the gpg-agent
cache expire mid-build (`Failure signing commit file: Pinentry: Timeout`). If
running headless, warm the agent right before the sign step (`gpg --clearsign`
once to cache the passphrase). Everything builds on `$TMPDIR` (tmpfs) so a
near-full `$HOME` doesn't trip ostree's min-free-space floor.

## Installing

Primary — the signed, auto-updating repo (tracked by `flatpak update`):

```shell
flatpak install --user https://superuser-miguel.github.io/Vivid_Gradience-repo/VividGradience.flatpakref
flatpak run io.github.superuser_miguel.VividGradience
```

Alternatively the one-off bundle from the GitHub Release — no auto-update, a
newer version means reinstalling it:

```shell
flatpak install --user ./VividGradience.flatpak
```

## Gotchas seen in practice

**Deps built from a GitHub archive tarball have unstable checksums.** A module
that sources `github.com/<x>/archive/refs/tags/<tag>.tar.gz` will fail its
`sha256` on a fresh (uncached) build, because GitHub re-generates those archives
with different compression over time. Local dev builds hide this by reusing the
flatpak-builder cache; the from-tag release build on a clean tmpfs state dir does
not. Prefer PyPI sdists/wheels with pinned hashes, and delete orphaned modules
(v0.2.0 tripped on a leftover `python-lxml` that only `svglib` had needed).

**GitHub Pages lags after `publish-repo.sh`.** The force-push lands on git
immediately, but the Pages CDN can serve the *previous* OSTree repo for a few
minutes, so the first `flatpak update` may pull the old version. Worse, updating
against a summary that changed underneath can spawn a `<name>1-origin`
`no-gpg-verify` remote. To verify a release cleanly: uninstall the app, delete
the local remote(s), then do a fresh `flatpak install` from the `.flatpakref`
and confirm the version — that re-establishes a single gpg-verified origin.

## Not Flathub

Flathub's requirements categorically prohibit AI-generated or AI-assisted code
and documentation. Vivid Gradience was built with substantial AI assistance and
cannot qualify as-built, so it is distributed independently. Do not submit it,
and do not obscure how it was built in order to pass review.
