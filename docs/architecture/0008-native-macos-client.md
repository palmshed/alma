# ADR 0008: Native macOS Client

**Date:** 2026-07-07
**Status:** Accepted

## Context

Alma currently has a web UI (React) and a static HTML UI. Both are
browser-based and share the same backend. As the product matures, a
desktop-class experience becomes valuable — native window management,
system-wide shortcuts, offline readiness, and deeper macOS integration
(Quick Look, Share Sheet, Spotlight, Dock menu).

The decision is not whether to build a desktop client, but what form it
should take and how it relates to the existing architecture.

## Decision

### Maintain a native SwiftUI client alongside the web UI

A native macOS app provides integration that a browser cannot:

- **Window management** — native titlebar, tabs, spaces, full-screen
- **System services** — drag-and-drop from Finder, Quick Look, Share Sheet
- **Notifications** — native Notification Center delivery
- **Menu bar** — global shortcuts and status without the browser open
- **Offline resilience** — local-first data access without network dependency

Electron or Tauri wrappers would inherit the browser's sandbox
limitations while adding bundle size and complexity. SwiftUI gives a
genuinely native feel with less code than AppKit.

### Reuse the existing HTTP API instead of rewriting business logic

The Python backend already implements:

- Conversation CRUD and search
- Message generation with thinking mode
- Attachment upload, storage, and lifecycle
- Anonymous identity management
- Health and configuration endpoints

The Swift client communicates with this backend over HTTP using
URLSession. This means:

- Feature work happens once in the backend
- Both UIs (React and Swift) get new capabilities simultaneously
- The verification suite covers both frontends with the same checks
- No business logic duplication across languages

Every API endpoint the web app uses is available to the Swift app. The
Swift app adds native UI on top of the same data layer.

### Ship a bundled local backend instead of reimplementing it in Swift

The backend is mature, verified, and integrates with platform services
(storage, mail, auth, notifications). Rewriting it in Swift would:

- Duplicate thousands of lines of tested Python
- Require parallel verification of two backend implementations
- Create a second platform services integration to maintain
- Lose the existing verification framework

Instead, the macOS `.app` bundle includes a Python runtime and the
existing backend. The app starts the backend on `localhost` at launch
and stops it on quit. The Swift UI is a client of this local server.

This keeps one backend, one verification system, and one truth:

- **Web UI** → HTTP → **Backend**
- **Swift UI** → HTTP → **Backend** (embedded or remote)

## Consequences

- The Swift app is a UI client, not a standalone application — it
  requires the backend running locally or remotely.
- Changes to API responses affect both frontends equally, which
  encourages backward-compatible API design.
- The bundled backend increases the app bundle size, but only by the
  Python runtime and project code — no second implementation.
- Verification extends naturally: the same scenarios run against both
  UIs, confirming they consume the same API correctly.
- Future macOS features (Spotlight indexing, Quick Look thumbnails) can
  call backend endpoints or storage directly from Swift.
- Platform services remain product-agnostic — the Swift app is just
  another consumer of the same infrastructure.
