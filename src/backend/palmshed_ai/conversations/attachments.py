# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

ATTACHMENT_SCHEMA_VERSION = 1

_KNOWN_ATTACHMENT_KEYS = {
    "id",
    "filename",
    "mime_type",
    "size",
    "checksum",
    "storage_key",
    "created_at",
    "metadata",
    "schema_version",
}


@dataclass
class Attachment:
    id: str
    filename: str
    mime_type: str
    size: int
    checksum: str
    storage_key: str
    created_at: str
    metadata: dict[str, Any] | None = None
    schema_version: int = ATTACHMENT_SCHEMA_VERSION
    _extra: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        d["id"] = self.id
        d["filename"] = self.filename
        d["mime_type"] = self.mime_type
        d["size"] = self.size
        d["checksum"] = self.checksum
        d["storage_key"] = self.storage_key
        d["created_at"] = self.created_at
        d["schema_version"] = self.schema_version
        if self.metadata:
            d["metadata"] = copy.deepcopy(self.metadata)
        d.update(self._extra)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Attachment:
        schema_version = d.get("schema_version", 0)
        if schema_version > ATTACHMENT_SCHEMA_VERSION:
            raise ValueError(
                f"Attachment schema version {schema_version} is newer than "
                f"supported version {ATTACHMENT_SCHEMA_VERSION}. Upgrade required."
            )
        extra = {
            k: copy.deepcopy(v) for k, v in d.items() if k not in _KNOWN_ATTACHMENT_KEYS
        }
        return cls(
            id=d["id"],
            filename=d["filename"],
            mime_type=d["mime_type"],
            size=d["size"],
            checksum=d["checksum"],
            storage_key=d["storage_key"],
            created_at=d["created_at"],
            metadata=copy.deepcopy(d.get("metadata")),
            schema_version=schema_version,
            _extra=extra,
        )
