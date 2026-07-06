# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from services.storage import StorageService, StorageError

from .models import Conversation, SCHEMA_VERSION

logger = logging.getLogger(__name__)

INDEX_VERSION = 1


@dataclass
class IndexEntry:
    id: str
    title: str
    mode: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "mode": self.mode,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IndexEntry:
        return cls(
            id=d["id"],
            title=d["title"],
            mode=d["mode"],
            created_at=d["created_at"],
            updated_at=d["updated_at"],
        )

    @classmethod
    def from_conversation(cls, conv: Conversation) -> IndexEntry:
        return cls(
            id=conv.id,
            title=conv.title,
            mode=conv.mode,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class ConversationStore:
    def __init__(self, storage: StorageService, owner_id: str) -> None:
        self._storage = storage
        self._owner_id = owner_id
        self._prefix = f"conversations/{owner_id}/"
        self._cache: dict[str, Conversation] = {}
        self._index_cache: Optional[dict[str, Any]] = None

    # ── public API ──

    def create(self, conversation: Conversation) -> Conversation:
        conversation.created_at = _now_utc()
        conversation.updated_at = conversation.created_at
        if conversation.schema_version == 0:
            conversation.schema_version = SCHEMA_VERSION
        self._save_conversation_file(conversation)
        self._update_index(conversation)
        self._cache[conversation.id] = conversation
        return conversation

    def save(self, conversation: Conversation) -> None:
        conversation.updated_at = _now_utc()
        self._save_conversation_file(conversation)
        self._update_index(conversation)
        self._cache[conversation.id] = conversation

    def load(self, conversation_id: str) -> Conversation | None:
        cached = self._cache.get(conversation_id)
        if cached is not None:
            return cached
        return self._load_conversation_file(conversation_id)

    def load_all(self) -> list[Conversation]:
        index = self._load_index()
        conversations: list[Conversation] = []
        for entry in index.get("conversations", {}).values():
            conv = self._load_conversation_file(entry["id"])
            if conv is not None:
                conversations.append(conv)
        return conversations

    def delete(self, conversation_id: str) -> bool:
        path = self._conversation_path(conversation_id)
        try:
            self._storage.delete(path)
        except StorageError:
            return False
        self._remove_from_index(conversation_id)
        self._cache.pop(conversation_id, None)
        return True

    def exists(self, conversation_id: str) -> bool:
        if conversation_id in self._cache:
            return True
        index = self._load_index()
        return conversation_id in index.get("conversations", {})

    # ── index management ──

    def _index_path(self) -> str:
        return f"{self._prefix}index.json"

    def _load_index(self) -> dict[str, Any]:
        if self._index_cache is not None:
            return self._index_cache
        try:
            _, raw = self._storage.download(self._index_path())
            self._index_cache = json.loads(raw.decode("utf-8"))
            return self._index_cache
        except (StorageError, json.JSONDecodeError):
            self._index_cache = {
                "version": INDEX_VERSION,
                "updated_at": _now_utc(),
                "conversations": {},
            }
            return self._index_cache

    def _write_index(self, index: dict[str, Any]) -> None:
        index["updated_at"] = _now_utc()
        self._storage.upload(
            self._index_path(),
            json.dumps(index, indent=2).encode("utf-8"),
            content_type="application/json",
        )

    def _update_index(self, conversation: Conversation) -> None:
        index = self._load_index()
        index.setdefault("conversations", {})
        index["conversations"][conversation.id] = IndexEntry.from_conversation(
            conversation
        ).to_dict()
        self._write_index(index)

    def _remove_from_index(self, conversation_id: str) -> None:
        index = self._load_index()
        index.get("conversations", {}).pop(conversation_id, None)
        self._write_index(index)

    # ── conversation file management ──

    def _conversation_path(self, conversation_id: str) -> str:
        return f"{self._prefix}{conversation_id}.json"

    def _save_conversation_file(self, conversation: Conversation) -> None:
        path = self._conversation_path(conversation.id)
        self._storage.upload(
            path,
            json.dumps(conversation.to_dict(), indent=2).encode("utf-8"),
            content_type="application/json",
        )

    def _load_conversation_file(self, conversation_id: str) -> Conversation | None:
        path = self._conversation_path(conversation_id)
        try:
            _, raw = self._storage.download(path)
            raw_dict = json.loads(raw.decode("utf-8"))
            return Conversation.from_dict(raw_dict)
        except (StorageError, json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Failed to load conversation %s: %s", conversation_id, exc)
            return None

    # ── discovery ──

    def list_ids(self) -> list[str]:
        index = self._load_index()
        return list(index.get("conversations", {}).keys())

    def index_entries(self) -> list[IndexEntry]:
        entries = self._discover_from_storage()
        if entries:
            self._index_cache = {
                "version": INDEX_VERSION,
                "updated_at": _now_utc(),
                "conversations": {e.id: e.to_dict() for e in entries},
            }
            return entries
        index = self._load_index()
        return [
            IndexEntry.from_dict(e) for e in index.get("conversations", {}).values()
        ]

    def _discover_from_storage(self) -> list[IndexEntry]:
        try:
            names = self._storage.list(self._prefix)
            entries = []
            for name in names:
                if not name.endswith(".json") or name == self._index_path():
                    continue
                conv_id = name.removeprefix(self._prefix).removesuffix(".json")
                conv = self._load_conversation_file(conv_id)
                if conv is not None:
                    entries.append(IndexEntry.from_conversation(conv))
            entries.sort(key=lambda e: e.created_at, reverse=True)
            return entries
        except (StorageError, Exception):
            return []
