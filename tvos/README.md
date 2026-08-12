# Map Editor (tvOS)

Apple TV app for polishing the map label layouts from the couch. It fetches
each map's `editor/<map>/base.png` + `labels.json` from this repo, overlays
the labels natively (same Inter fonts, stroke halo), lets you move and
resize them with the Siri Remote, and saves the result as
`overrides/<map>.json` through the GitHub API. A GitHub Action then
re-renders the real PNGs. Protocol details: `docs/editor-protocol.md`.

## Building

The Xcode project is generated from `project.yml` with
[XcodeGen](https://github.com/yonaskolb/XcodeGen):

```sh
brew install xcodegen
cd tvos && xcodegen
open MapEditor.xcodeproj
```

Select your development team in Signing & Capabilities (or set
`DEVELOPMENT_TEAM` in project.yml), pick your Apple TV as the run
destination (Devices & Simulators → pair with the TV), and Run. With a paid
developer account the installed app stays valid for about a year.

CI (`.github/workflows/tvos.yml`) builds and tests every push that touches
`tvos/`.

## One-time setup on the TV

Create a fine-grained personal access token at
<https://github.com/settings/personal-access-tokens/new>:
repository access = only `dvrensk/static-tv-maps`, permissions =
Contents: Read and write. In the app, open **Ajustes** and paste it (easiest
with the iPhone keyboard that pops up when the field is focused). It is
stored in the tvOS keychain.

## Remote controls

| Mode | Controls |
|---|---|
| Browse | ◀︎/▶︎ select label · click = move it · long-press = resize · ▶︎(play/pause) = save |
| Move | d-pad taps nudge 1 km · touchpad pan drags · click = confirm · menu = cancel |
| Resize | ▲/▼ ±2 pt (warns below the 24 pt floor) · click = confirm · menu = cancel |

Saving commits only the labels you changed, merged over whatever the
overrides file already contained. The `apply-label-overrides` workflow
re-renders the affected map in ~2 minutes.
