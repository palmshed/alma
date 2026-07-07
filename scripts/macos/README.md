# macOS Packaging

## Unsigned builds

Alma intentionally ships with a clean ad-hoc signature.

Do **not** remove the signature. macOS 15 expects a structurally valid
bundle. Removing the signature results in launch failures (POSIX 163),
while SwiftPM's default ad-hoc signature may reference resources that
do not exist and trigger a "damaged" warning.

The packaging script therefore reapplies a clean ad-hoc signature:

```
codesign -s - --force Alma.app
```

Code signing with a Developer ID and notarization are separate
milestones.

## Scripts

| Script | Purpose |
|--------|---------|
| `build.sh` | Build Alma.app from Swift source |
| `generate-icons.sh` | Render canonical logo.svg into AppIcon.appiconset |
| `generate-dmg-resources.sh` | Render background.svg into DMG background.png |
| `generate-dsstore.py` | Generate .DS_Store with background alias and window settings |
| `package.sh` | Package Alma.app into Alma.dmg |
| `verify.sh` | Verify bundle structure and DMG contents |

Run all three locally:

```
./scripts/macos/build.sh
./scripts/macos/package.sh
./scripts/macos/verify.sh
```

## DS_Store generation

The DMG `.DS_Store` is generated from scratch during packaging, not
copied from a template. This keeps the installer deterministic and
reviewable.

### Implementation note

Finder ignores `backgroundImageBookmark` (Bookmark format, magic `book`)
for DMG backgrounds on macOS 15. Use `backgroundImageAlias` (Alias
format, magic `\0\0\0\0`) instead. The generator uses
`mac_alias.Alias.for_file()` and stores the result under the
`backgroundImageAlias` key in the `icvp` plist.
