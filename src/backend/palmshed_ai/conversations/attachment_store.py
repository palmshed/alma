# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import logging
from typing import Optional

from services.storage import StorageService, StorageError

from .attachments import Attachment

logger = logging.getLogger(__name__)

ATTACHMENTS_PREFIX = "attachments/"
METADATA_PREFIX = "attachment-metadata/"


class AttachmentStoreError(Exception):
    pass


class AttachmentStore:
    def __init__(self, storage: StorageService) -> None:
        self._storage = storage

    # ── public API ──

    def save(self, attachment: Attachment, data: bytes) -> None:
        self._save_binary(attachment, data)
        self._save_metadata(attachment)

    def load_metadata(self, attachment_id: str) -> Optional[Attachment]:
        return self._load_metadata(attachment_id)

    def load_data(self, attachment_id: str) -> Optional[bytes]:
        return self._load_data(attachment_id)

    def load_with_data(self, attachment_id: str) -> Optional[tuple[Attachment, bytes]]:
        attachment = self.load_metadata(attachment_id)
        if attachment is None:
            return None
        data = self._load_data(attachment_id)
        if data is None:
            return None
        return attachment, data

    def delete(self, attachment_id: str) -> bool:
        deleted_meta = self._delete_metadata(attachment_id)
        deleted_bin = self._delete_binary(attachment_id)
        return deleted_meta or deleted_bin

    def list_ids(self) -> list[str]:
        ids: set[str] = set()
        try:
            names = self._storage.list(METADATA_PREFIX)
            for name in names:
                if name.endswith(".json"):
                    att_id = name.removeprefix(METADATA_PREFIX).removesuffix(".json")
                    ids.add(att_id)
        except StorageError:
            pass
        return sorted(ids)

    def update_metadata(self, attachment_id: str, updates: dict[str, object]) -> bool:
        """Update specific keys in the attachment's metadata dict.

        The metadata dict is the application-defined metadata bag on the
        Attachment object, not the top-level fields. This is used to store
        non-ownership references such as conversation_id and message_id.

        Returns True if the metadata was updated, False if the attachment
        does not exist.
        """
        attachment = self._load_metadata(attachment_id)
        if attachment is None:
            return False
        if attachment.metadata is None:
            attachment.metadata = {}
        attachment.metadata.update(updates)
        self._save_metadata(attachment)
        return True

    def metadata_exists(self, attachment_id: str) -> bool:
        return self._storage.exists(self._metadata_path(attachment_id))

    def binary_exists(self, attachment_id: str) -> bool:
        return self._storage.exists(self._binary_path(attachment_id))

    # ── path helpers ──

    @staticmethod
    def _binary_path(attachment_id: str) -> str:
        return f"{ATTACHMENTS_PREFIX}{attachment_id}.bin"

    @staticmethod
    def _metadata_path(attachment_id: str) -> str:
        return f"{METADATA_PREFIX}{attachment_id}.json"

    # ── binary storage ──

    def _save_binary(self, attachment: Attachment, data: bytes) -> None:
        path = self._binary_path(attachment.id)
        self._storage.upload(
            path,
            data,
            content_type=attachment.mime_type,
        )

    def _load_data(self, attachment_id: str) -> Optional[bytes]:
        path = self._binary_path(attachment_id)
        try:
            _, data = self._storage.download(path)
            return data
        except StorageError:
            return None

    def _delete_binary(self, attachment_id: str) -> bool:
        path = self._binary_path(attachment_id)
        try:
            self._storage.delete(path)
            return True
        except StorageError:
            return False

    # ── metadata storage ──

    def _save_metadata(self, attachment: Attachment) -> None:
        path = self._metadata_path(attachment.id)
        self._storage.upload(
            path,
            json.dumps(attachment.to_dict(), indent=2).encode("utf-8"),
            content_type="application/json",
        )

    def _load_metadata(self, attachment_id: str) -> Optional[Attachment]:
        path = self._metadata_path(attachment_id)
        try:
            _, raw = self._storage.download(path)
            raw_dict = json.loads(raw.decode("utf-8"))
            return Attachment.from_dict(raw_dict)
        except (StorageError, json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning(
                "Failed to load attachment metadata %s: %s", attachment_id, exc
            )
            return None

    def _delete_metadata(self, attachment_id: str) -> bool:
        path = self._metadata_path(attachment_id)
        try:
            self._storage.delete(path)
            return True
        except StorageError:
            return False
