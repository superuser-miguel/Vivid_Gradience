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

**2. Commit and tag.**

```shell
git commit -am "Release vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

The tag must be pushed *before* the next step — the release build fetches the
source over the network, so an unpushed tag cannot be resolved.

**3. Note the commit the tag points at.**

```shell
git rev-parse vX.Y.Z
```

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
s["commit"] = subprocess.check_output(["git", "rev-parse", TAG]).decode().strip()
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

**6. Publish.**

```shell
gh release create vX.Y.Z VividGradience.flatpak \
  --title "Vivid Gradience vX.Y.Z" --notes "…"
```

`repo-release/`, `build-dir-release/` and `*.flatpak` are all gitignored —
release artifacts are published, never committed.

## Installing a bundle

```shell
flatpak install --user ./VividGradience.flatpak
flatpak run io.github.superuser_miguel.VividGradience
```

A bundle carries **no auto-update**; installing a newer release means
downloading and reinstalling it. A hosted repo plus a `.flatpakref` would give
updates, and isn't set up.

## Not Flathub

Flathub's requirements categorically prohibit AI-generated or AI-assisted code
and documentation. Vivid Gradience was built with substantial AI assistance and
cannot qualify as-built, so it is distributed independently. Do not submit it,
and do not obscure how it was built in order to pass review.
