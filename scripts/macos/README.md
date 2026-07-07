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
| `package.sh` | Package Alma.app into Alma.dmg |
| `verify.sh` | Verify bundle structure and DMG contents |

Run all three locally:

```
./scripts/macos/build.sh
./scripts/macos/package.sh
./scripts/macos/verify.sh
```
