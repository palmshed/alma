# ADR 0005: Conversation Model

**Date:** 2026-07-05
**Status:** Accepted

## Context

Conversations are Alma's primary product concept — every user interaction
happens within a conversation. The model must be designed for the product,
not the current UI, because conversations will outlive any single interface
(sidebar, search, export, sharing, multi-device).

## Decision

### Conversations are a first-class product feature

Conversations are not transient UI state. They are persisted entities with
a stable schema, independent of React components, scroll positions, or
panel states.

### Storage service owns persistence

The existing `StorageService` (platform layer) owns all I/O. The
conversation model layer handles only validation, serialization, and
deserialization. This separation means storage provider swaps (Mock,
Local, Cloud) do not affect the model.

### UI-independent schema

The model contains no React state — no expanded panels, loading flags,
scroll positions, or animation state. Every conversation is fully
serializable and deserializable without information loss.

### Schema versioning

A `schema_version` field (integer, starts at 1) is present from day one.
This provides a clean migration path if the model evolves later.

### Serialization format

JSON. Ubiquitous, human-readable, universally supported across platforms.

### Identifiers

UUID v4 strings. Stable, unique, no sequential guessing.

### Timestamps

ISO 8601 UTC strings (e.g. `2026-07-05T12:00:00Z`). Machine-parseable,
timezone-agnostic, sortable.

### Additive evolution only

New fields may be added in future schema versions. Existing conversations
must continue to load. Unknown fields are preserved during round-trip
serialization. No breaking changes to existing fields.

## Consequences

- The conversation model layer has zero dependencies on Flask, React, or
  any UI framework.
- Persistence is a wiring concern handled entirely by StorageService.
- Schema versioning ensures forward compatibility without migrations.
- JSON serialization makes debugging, inspection, and export trivial.
- UUIDs prevent ID collision across devices or users.
- UI changes never require model changes, and model changes never require
  migration scripts (as long as they are additive).
