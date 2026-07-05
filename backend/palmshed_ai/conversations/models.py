# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = 1

_KNOWN_MESSAGE_KEYS = {"id", "role", "timestamp", "content",
                       "thinking", "image", "attachments", "metadata"}
_KNOWN_CONVERSATION_KEYS = {"id", "title", "mode", "schema_version",
                            "created_at", "updated_at", "messages", "metadata"}


@dataclass
class Message:
    id: str
    role: str
    timestamp: str
    content: str
    thinking: str | None = None
    image: str | None = None
    attachments: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None
    _extra: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        d["id"] = self.id
        d["role"] = self.role
        d["timestamp"] = self.timestamp
        d["content"] = self.content
        if self.thinking is not None:
            d["thinking"] = self.thinking
        if self.image is not None:
            d["image"] = self.image
        if self.attachments is not None:
            d["attachments"] = copy.deepcopy(self.attachments)
        if self.metadata:
            d["metadata"] = copy.deepcopy(self.metadata)
        d.update(self._extra)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Message:
        extra = {k: v for k, v in d.items() if k not in _KNOWN_MESSAGE_KEYS}
        return cls(
            id=d["id"],
            role=d["role"],
            timestamp=d["timestamp"],
            content=d["content"],
            thinking=d.get("thinking"),
            image=d.get("image"),
            attachments=copy.deepcopy(d.get("attachments")),
            metadata=copy.deepcopy(d.get("metadata")),
            _extra=extra,
        )


@dataclass
class Conversation:
    id: str
    title: str
    mode: str
    created_at: str
    updated_at: str
    messages: list[Message]
    schema_version: int = SCHEMA_VERSION
    metadata: dict[str, Any] | None = None
    _extra: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        d["id"] = self.id
        d["title"] = self.title
        d["mode"] = self.mode
        d["schema_version"] = self.schema_version
        d["created_at"] = self.created_at
        d["updated_at"] = self.updated_at
        d["messages"] = [m.to_dict() for m in self.messages]
        if self.metadata:
            d["metadata"] = copy.deepcopy(self.metadata)
        d.update(self._extra)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Conversation:
        schema_version = d.get("schema_version", 0)
        if schema_version > SCHEMA_VERSION:
            raise ValueError(
                f"Conversation schema version {schema_version} is newer than "
                f"supported version {SCHEMA_VERSION}. Upgrade required."
            )
        extra = {k: v for k, v in d.items() if k not in _KNOWN_CONVERSATION_KEYS}
        messages = [Message.from_dict(m) for m in d.get("messages", [])]
        return cls(
            id=d["id"],
            title=d["title"],
            mode=d["mode"],
            schema_version=schema_version,
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            messages=messages,
            metadata=copy.deepcopy(d.get("metadata")),
            _extra=extra,
        )
