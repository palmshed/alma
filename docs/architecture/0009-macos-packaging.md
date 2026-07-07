# ADR 0009: Native macOS Packaging

**Date:** 2026-07-08
**Status:** Accepted

## Context

The native macOS client (ADR 0008) currently requires users to clone
the repository and build from source with Swift. As the client matures
into a usable application, distributing a pre-built binary removes the
primary barrier to adoption: requiring a Swift development environment.

The decision is not whether to distribute binaries, but what form the
distribution should take and how to produce it sustainably.

## Decision

### Distribute a DMG image instead of requiring a source build

A DMG provides the familiar Mac installation experience: download, open,
drag to Applications. Alternatives were considered:

- **Source-only**: lowest maintenance, but requires Xcode and
  dependencies. Acceptable during development, not for general use.
- **Homebrew tap**: appeals to power users, but adds a distribution
  channel to maintain. Better as a later addition.
- **.zip of .app**: simpler to produce than DMG, but loses the visual
  installation metaphor (background, icon positioning, Applications
  alias) that Mac users expect.
- **Mac App Store**: requires Apple Developer enrollment, code signing,
  notarization, and approval delays. Premature for a pre-v1 product.

The DMG is the lowest-friction distribution format for an unsigned open
source Mac app.

### Package through GitHub Actions, not locally

Packaging in CI rather than on a developer machine:

- Produces bit-for-bit reproducible artifacts from a clean environment
- Eliminates "works on my machine" discrepancies between development
  and release builds
- Runs packaging scripts on every tagged release without manual
  intervention
- Archives build artifacts and release assets in one place (GitHub)
- Does not require developers to install DMG tooling locally

The GitHub Release asset attachment path means no separate storage
service is needed. The DMG lives alongside the source archive.

### Keep packaging, signing, and notarization as separate milestones

Packaging, code signing, Hardened Runtime, notarization, and stapling
are independent concerns that are often combined into a single
"distribution" task. Combining them:

- Delays the first shippable binary until all Apple developer
  prerequisites are met
- Couples CI workflow changes with Apple account setup, making each
  harder to debug independently
- Burdens the initial packaging milestone with concerns that may change
  as the project's Apple Developer relationship evolves

Instead, each capability lands in its own milestone:

1. **Packaging** — produce a working unsigned DMG from CI (v0.3.3)
2. **Signing** — remove the unidentified-developer warning (v0.3.4)
3. **Distribution** — notarize, staple, optional auto-update (v0.3.5)

This ordering means packaging can be verified independently. If the DMG
has structural problems, they are found before signing and notarization
configuration is added on top.

## Consequences

- Users with a GitHub account can download a runnable Alma from the
  Releases page without any developer tooling installed.
- The unsigned DMG will show a Gatekeeper warning on first launch,
  which is acceptable for an open source project at this stage.
- A `scripts/macos/` directory centralises all packaging knowledge —
  CI configuration stays thin and local packaging mirrors CI packaging.
- GitHub Actions macOS runner minutes will be consumed on each tagged
  release, but release cadence is low enough that this is not a concern.
- The DMG format may change if future distribution methods (Homebrew,
  Mac App Store) replace direct download as the primary channel.

---

### DS_Store generation (v0.3.4+)

The DMG `.DS_Store` is generated during packaging by
`scripts/macos/generate-dsstore.py` using the `ds_store` and
`mac_alias` Python libraries.

**Decision**

Generate `.DS_Store` programmatically rather than committing a binary
template or relying on AppleScript to configure Finder view state.

**Rationale**

- AppleScript's `set background picture` no longer persists Finder
  window configuration to `.DS_Store` on macOS 15 — the background
  image, icon size, and arrangement settings are lost when the window
  is closed or the volume is remounted.
- A generated `.DS_Store` is deterministic, reviewable, and
  source-controlled as code.
- CI can produce identical installers without manual Finder interaction
  or GUI scripting.
- No opaque binary template is committed to the repository.

**Implementation detail**

Finder ignores `backgroundImageBookmark` (NSData containing a modern
Bookmark record, magic `b"book"`) for DMG background images. It accepts
`backgroundImageAlias` (NSData containing an old-style Alias record,
magic `b"\0\0\0\0"`). The generator therefore uses
`mac_alias.Alias.for_file()` and stores the result under the
`backgroundImageAlias` plist key.

`mac_alias` v2.2.3 uses 32-bit `I` format for CNID path entries in
alias records, which fails on APFS volumes with 64-bit inode numbers.
The installed copy is patched to use `Q` format in both virtualenvs
(`.build-dsstore/` and `/tmp/dsstore-env/`).
