# ADR 0007: Attachment Model

**Date:** 2026-07-06
**Status:** Accepted

## Context

Alma needs to attach files to conversations. The design must determine
where attachments live in the domain model and how they are stored.

## Decision

### Attachments belong to messages, not conversations

Every file has context — it was uploaded as part of a specific message.
Attaching to the message rather than the conversation keeps the model
simple and enables:

- **Search** — find files by their surrounding message text
- **Export** — export a message and its files together
- **Retrieval** — retrieve files only when the message is loaded
- **Sharing** — share a message with its attachments intact
- **Cleanup** — delete files when the message is deleted

A conversation never references attachments directly. It stores
messages, and messages store attachment IDs.

### Attachment storage is flat and independent of conversation layout

Attachment bytes are stored as:

```
attachments/<attachment-id>.bin
```

Metadata is stored as:

```
attachment-metadata/<attachment-id>.json
```

The metadata contains `conversation_id` and `message_id` as references,
not as path components. This avoids baking the conversation hierarchy
into the storage layer and gives flexibility to:

- **Move a message** between conversations without rewriting file paths
- **Split conversations** without relocating attachment blobs
- **Quote or forward messages** with their attachments
- **Deduplicate files** when the same blob is referenced from multiple
  messages
- **Evolve storage independently** of the conversation model

### The Attachment domain object is independent of its relationships

The `Attachment` model contains only its own identity and properties:

- `id` — unique identifier
- `filename` — original upload name
- `mime_type` — validated media type
- `size` — file size in bytes
- `checksum` — SHA-256 of file bytes
- `storage_key` — path within the storage provider
- `created_at` — timestamp
- `metadata` — optional key-value map for extensibility
- `schema_version` — for forward compatibility
- preserved unknown fields — for safe deserialization

The model does not contain `conversation_id` or `message_id`. Those are
metadata of the *relationship*, not properties of the attachment
itself. The message that references the attachment owns the
relationship.

## Consequences

- Attachments are first-class domain objects with their own lifecycle
  and identity.
- Messages reference attachments by ID only — the attachment exists
  independently.
- Storage layout is flat, making it easy to reorganize conversations
  without moving file bytes.
- The same attachment can conceptually be referenced from multiple
  messages without storage duplication.
- Adding attachment sharing or deduplication later requires no storage
  migration.
- The relationship between attachment, message, and conversation is
  always explicit in metadata, never implicit in paths.
