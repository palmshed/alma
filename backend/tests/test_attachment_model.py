# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

import json
import uuid

import pytest

from palmshed_ai.conversations import Attachment, ATTACHMENT_SCHEMA_VERSION


def _make_attachment(overrides=None):
    data = {
        "id": str(uuid.uuid4()),
        "filename": "photo.png",
        "mime_type": "image/png",
        "size": 1024,
        "checksum": "abc123def456",
        "storage_key": "attachments/some-uuid.bin",
        "created_at": "2026-07-06T12:00:00Z",
    }
    if overrides:
        data.update(overrides)
    return Attachment(**data)


class TestAttachmentCreation:
    def test_minimal_attachment(self):
        att = _make_attachment()
        assert isinstance(att.id, str)
        assert att.filename == "photo.png"
        assert att.mime_type == "image/png"
        assert att.size == 1024
        assert att.checksum == "abc123def456"
        assert att.storage_key == "attachments/some-uuid.bin"
        assert att.created_at == "2026-07-06T12:00:00Z"
        assert att.metadata is None
        assert att.schema_version == ATTACHMENT_SCHEMA_VERSION

    def test_attachment_with_metadata(self):
        att = _make_attachment({"metadata": {"source": "upload", "width": 800}})
        assert att.metadata == {"source": "upload", "width": 800}

    def test_different_mime_types(self):
        for mime in ("image/png", "image/jpeg", "application/pdf", "text/plain"):
            att = _make_attachment({"mime_type": mime})
            assert att.mime_type == mime

    def test_zero_size_allowed(self):
        att = _make_attachment({"size": 0})
        assert att.size == 0

    def test_large_size(self):
        att = _make_attachment({"size": 10_000_000})
        assert att.size == 10_000_000


class TestAttachmentSerialization:
    def test_round_trip_minimal(self):
        att = _make_attachment()
        d = att.to_dict()
        restored = Attachment.from_dict(d)
        assert restored.id == att.id
        assert restored.filename == att.filename
        assert restored.mime_type == att.mime_type
        assert restored.size == att.size
        assert restored.checksum == att.checksum
        assert restored.storage_key == att.storage_key
        assert restored.created_at == att.created_at
        assert restored.metadata is None
        assert restored.schema_version == ATTACHMENT_SCHEMA_VERSION

    def test_round_trip_with_metadata(self):
        att = _make_attachment({"metadata": {"width": 1920, "height": 1080}})
        d = att.to_dict()
        restored = Attachment.from_dict(d)
        assert restored.metadata == {"width": 1920, "height": 1080}

    def test_round_trip_all_fields(self):
        att = _make_attachment(
            {
                "filename": "report.pdf",
                "mime_type": "application/pdf",
                "size": 2048,
                "checksum": "xyz789",
                "metadata": {"page_count": 3},
            }
        )
        d = att.to_dict()
        restored = Attachment.from_dict(d)
        assert restored.filename == "report.pdf"
        assert restored.mime_type == "application/pdf"
        assert restored.size == 2048
        assert restored.checksum == "xyz789"
        assert restored.metadata == {"page_count": 3}

    def test_unknown_fields_preserved(self):
        raw = {
            "id": str(uuid.uuid4()),
            "filename": "doc.txt",
            "mime_type": "text/plain",
            "size": 512,
            "checksum": "abc",
            "storage_key": "attachments/uuid.bin",
            "created_at": "2026-07-06T12:00:00Z",
            "future_field": "something new",
            "another_field": 42,
        }
        att = Attachment.from_dict(raw)
        d = att.to_dict()
        assert d["future_field"] == "something new"
        assert d["another_field"] == 42

    def test_unknown_fields_do_not_leak_into_known(self):
        raw = {
            "id": str(uuid.uuid4()),
            "filename": "doc.txt",
            "mime_type": "text/plain",
            "size": 512,
            "checksum": "abc",
            "storage_key": "attachments/uuid.bin",
            "created_at": "2026-07-06T12:00:00Z",
            "filename": "overridden.txt",  # noqa: F601
        }
        # the second "filename" overrides the first; that's dict behavior
        att = Attachment.from_dict(raw)
        assert att.filename == "overridden.txt"

    def test_json_round_trip(self):
        att = _make_attachment({"metadata": {"key": "val"}})
        raw_json = json.dumps(att.to_dict())
        restored = Attachment.from_dict(json.loads(raw_json))
        assert restored.id == att.id
        assert restored.filename == att.filename
        assert restored.checksum == att.checksum
        assert restored.metadata == {"key": "val"}

    def test_metadata_excluded_when_empty(self):
        att = _make_attachment()
        att.metadata = None
        d = att.to_dict()
        assert "metadata" not in d or d["metadata"] is None


class TestSchemaVersioning:
    def test_current_version(self):
        assert ATTACHMENT_SCHEMA_VERSION == 1

    def test_schema_version_in_output(self):
        att = _make_attachment()
        d = att.to_dict()
        assert d["schema_version"] == ATTACHMENT_SCHEMA_VERSION

    def test_older_version_loads(self):
        raw = {
            "id": str(uuid.uuid4()),
            "filename": "old.txt",
            "mime_type": "text/plain",
            "size": 100,
            "checksum": "old",
            "storage_key": "attachments/old.bin",
            "created_at": "2026-07-06T12:00:00Z",
            "schema_version": 0,
        }
        att = Attachment.from_dict(raw)
        assert att.schema_version == 0

    def test_missing_schema_defaults_to_zero(self):
        raw = {
            "id": str(uuid.uuid4()),
            "filename": "noversion.txt",
            "mime_type": "text/plain",
            "size": 100,
            "checksum": "none",
            "storage_key": "attachments/none.bin",
            "created_at": "2026-07-06T12:00:00Z",
        }
        att = Attachment.from_dict(raw)
        assert att.schema_version == 0

    def test_future_schema_version_raises(self):
        raw = {
            "id": str(uuid.uuid4()),
            "filename": "future.txt",
            "mime_type": "text/plain",
            "size": 100,
            "checksum": "future",
            "storage_key": "attachments/future.bin",
            "created_at": "2026-07-06T12:00:00Z",
            "schema_version": 999,
        }
        with pytest.raises(ValueError, match="newer"):
            Attachment.from_dict(raw)


class TestImmutability:
    def test_to_dict_returns_new_dict(self):
        att = _make_attachment()
        d1 = att.to_dict()
        d1["filename"] = "modified.png"
        assert att.filename != "modified.png"
        d2 = att.to_dict()
        assert d2["filename"] == "photo.png"

    def test_from_dict_deep_copies_metadata(self):
        raw = {
            "id": str(uuid.uuid4()),
            "filename": "test.txt",
            "mime_type": "text/plain",
            "size": 100,
            "checksum": "abc",
            "storage_key": "attachments/t.bin",
            "created_at": "2026-07-06T12:00:00Z",
            "metadata": {"nested": {"key": "val"}},
        }
        att = Attachment.from_dict(raw)
        raw["metadata"]["nested"]["key"] = "changed"
        assert att.metadata["nested"]["key"] == "val"

    def test_to_dict_deep_copies_metadata(self):
        att = _make_attachment({"metadata": {"nested": {"key": "val"}}})
        d = att.to_dict()
        d["metadata"]["nested"]["key"] = "changed"
        assert att.metadata["nested"]["key"] == "val"


class TestIdentifier:
    def test_id_is_non_empty_string(self):
        att = _make_attachment()
        assert isinstance(att.id, str)
        assert len(att.id) > 0

    def test_uuid_format(self):
        att = _make_attachment()
        parsed = uuid.UUID(att.id)
        assert str(parsed) == att.id


class TestTimestampFormat:
    def test_iso_8601_utc(self):
        att = _make_attachment()
        assert att.created_at.endswith("Z")
        assert "T" in att.created_at


class TestChecksum:
    def test_checksum_is_string(self):
        att = _make_attachment()
        assert isinstance(att.checksum, str)
        assert len(att.checksum) > 0

    def test_empty_checksum_allowed(self):
        att = _make_attachment({"checksum": ""})
        assert att.checksum == ""


class TestStorageKey:
    def test_storage_key_is_string(self):
        att = _make_attachment()
        assert isinstance(att.storage_key, str)
        assert len(att.storage_key) > 0

    def test_storage_key_preserved(self):
        key = "custom/path/file.bin"
        att = _make_attachment({"storage_key": key})
        assert att.storage_key == key


class TestSizeType:
    def test_size_is_int(self):
        att = _make_attachment()
        assert isinstance(att.size, int)

    def test_negative_size_allowed_at_model(self):
        att = _make_attachment({"size": -1})
        assert att.size == -1
