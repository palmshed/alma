# Changelog

## v0.2.0 — Conversation History

*Conversation persistence, sidebar management, and search.*

### Added
- Conversation model with schema versioning (`SCHEMA_VERSION=1`), forward
  compatibility via `_extra` dict, UUID identifiers, ISO 8601 timestamps.
- `ConversationStore` wrapping StorageService — atomic create/save/load/delete
  with corruption-tolerant index.
- Conversation CRUD API routes (`GET/POST /api/conversations`,
  `GET/PUT/DELETE /api/conversations/<id>`) with proper HTTP semantics
  (204 on delete, 400 on validation failure, 404 on missing, server-side UUIDs).
- Auto-generated conversation titles from first user message (60 chars)
  with `title_is_manual` flag — manual renames are never overwritten.
- Sidebar component (React + static parity) with conversation list,
  newest-first ordering, inline rename, delete with confirmation dialog,
  empty state, loading state, active highlighting, relative dates.
- Optimistic rename and delete with rollback on API failure.
- Sidebar search — case-insensitive title filtering with `<mark>`
  highlighting, clear button, "No conversations found." state,
  Cmd+K / Ctrl+K keyboard shortcut.
- Conversation restore on reload — active conversation persisted to
  `localStorage` and auto-loaded on mount with `restoring` guard.
- Mode persistence — conversation `mode` (canvas/thinking/web/images)
  saved and restored on sidebar selection.
- Thinking mode verified — Gemini `include_thoughts` rendering:
  thought parts display separately from final answer. SDK correctly
  handles `thought` field in API response.
- Image restoration — `imageUrl` loaded from last assistant message
  with `image` field.
- E2E conversation switching verification — creates two conversations
  with distinct modes, switches between them, verifies state preservation.
- 5 frontend test cases for search (filtering, clear, Cmd+K, empty state).

### Changed
- `__version__` bumped to 0.2.0.
- Frontend API service: `listConversations()`, `getConversation()`,
  `createConversation()`, `updateConversation()`, `deleteConversation()`.
- `useConversation` hook: `loadConversation(conv)` for restoring
  past conversations.
- `alma verify` static checks: 10 checks including sidebar search.
- All static (deploy/static/web/) implementation updated for parity
  with React — optimistic rename/delete, error banner, delete dialog
  focus trap, aria/role accessibility, image restoration, search.

### Fixed
- API HTTP semantics: DELETE returns 204 with no body; POST validates
  `messages`/`mode` returns 400; PUT validates existence returns 404.
- YAML heredoc issue in E2E workflow — replaced with `python3 -c` one-liner.
- SDK: `generate_text_with_thinking()` properly skips parts without text.

## v0.1.0 — Platform Engineering

*Platform services layer with unified verification.* [Frozen]

### Added
- Four platform services (Mail, Auth, Storage, Notifications) with ABC
  providers, centralized config from env, health checks, metrics, logging.
- `PlatformManager` — single entry point for all services.
- Provider selection via env vars (`MAIL_PROVIDER`, `AUTH_PROVIDER`,
  `STORAGE_PROVIDER`, `NOTIFICATIONS_DEFAULT_CHANNEL`).
- Mock provider as default for every service — zero credentials needed.
- `alma verify` CLI with platform + application checks, `--json` output,
  per-check sub-commands.
- UI verification module (`verify_ui.py`) with capability detection,
  static frontend checks, Playwright browser verifier, render fidelity
  checks (10 features).
- ADRs 0001–0004 documenting architecture decisions.
- CI, smoke, E2E, and release GitHub Actions workflows.
- Verification history archived on successful E2E runs.

### Changed
- `GET /api/health` returns all four services via `platform.health()`.
- Static frontend parity established for all features.
