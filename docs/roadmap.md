# Roadmap

```
v0.1.0 ─── Platform Engineering ──── Frozen
v0.2.0 ─── Conversation History ──── Complete
v0.3.0 ─── Rich Conversations ────── Next
v0.4.0 ─── Accounts ──────────────── Future
v0.5.0 ─── Sharing ───────────────── Future
```

## Completed

**v0.1.0 — Platform**
Mail, Auth, Storage, Notifications services with ABC providers, config,
metrics, health, verify CLI. PlatformManager single entry point.
Published and frozen.

**v0.2.0 — Conversation History**
Persist, rename, delete, sidebar, auto titles, restore on reload,
conversation switching, search. Conversation model with schema
versioning. E2E browser verification and render fidelity checks.

## Next

**v0.3.0 — Rich Conversations**
- File attachments
- Drag & drop
- Image uploads
- Paste images
- Attachment previews
- Download attachments
- Storage integration
- Browser E2E
- alma verify

Builds on the conversation model and Storage service established in
v0.2.0.

## Future

**v0.4.0 — Accounts**
Authentication, user profiles, per-user conversation isolation.

**v0.5.0 — Sharing**
Shared conversations, public links, collaborative features.
