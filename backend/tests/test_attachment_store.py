# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

import uuid

from services.storage import StorageService, StorageConfig

from palmshed_ai.conversations import Attachment, AttachmentStore


def _make_attachment(overrides=None) -> Attachment:
    data = {
        "id": str(uuid.uuid4()),
        "filename": "photo.png",
        "mime_type": "image/png",
        "size": 1024,
        "checksum": "abc123",
        "storage_key": f"attachments/{uuid.uuid4()}.bin",
        "created_at": "2026-07-06T12:00:00Z",
    }
    if overrides:
        data.update(overrides)
    return Attachment(**data)


def _make_store() -> tuple[AttachmentStore, StorageService]:
    config = StorageConfig(provider="mock", bucket="alma-test")
    storage = StorageService(config=config)
    store = AttachmentStore(storage=storage)
    return store, storage


class TestAttachmentStoreSave:
    def test_save_and_load_metadata(self):
        store, _storage = _make_store()
        att = _make_attachment()
        store.save(att, b"fake-image-data")
        loaded = store.load_metadata(att.id)
        assert loaded is not None
        assert loaded.id == att.id
        assert loaded.filename == att.filename
        assert loaded.mime_type == att.mime_type
        assert loaded.size == att.size
        assert loaded.checksum == att.checksum

    def test_save_and_load_data(self):
        store, _storage = _make_store()
        att = _make_attachment()
        data = b"hello-world-data"
        store.save(att, data)
        loaded_data = store.load_data(att.id)
        assert loaded_data == data

    def test_save_and_load_with_data(self):
        store, _storage = _make_store()
        att = _make_attachment()
        data = b"complete-data"
        store.save(att, data)
        result = store.load_with_data(att.id)
        assert result is not None
        loaded_att, loaded_data = result
        assert loaded_att.id == att.id
        assert loaded_data == data

    def test_save_multiple_attachments(self):
        store, _storage = _make_store()
        att1 = _make_attachment()
        att2 = _make_attachment()
        store.save(att1, b"data1")
        store.save(att2, b"data2")
        assert store.load_metadata(att1.id) is not None
        assert store.load_metadata(att2.id) is not None
        assert store.load_data(att1.id) == b"data1"
        assert store.load_data(att2.id) == b"data2"

    def test_save_preserves_metadata(self):
        store, _storage = _make_store()
        att = _make_attachment({"metadata": {"width": 800, "height": 600}})
        store.save(att, b"data")
        loaded = store.load_metadata(att.id)
        assert loaded is not None
        assert loaded.metadata == {"width": 800, "height": 600}

    def test_save_large_data(self):
        store, _storage = _make_store()
        att = _make_attachment()
        large_data = b"x" * 100_000
        store.save(att, large_data)
        loaded = store.load_data(att.id)
        assert loaded == large_data




class TestAttachmentStoreLoad:
    def test_load_nonexistent_metadata_returns_none(self):
        store, _storage = _make_store()
        result = store.load_metadata("nonexistent-id")
        assert result is None

    def test_load_nonexistent_data_returns_none(self):
        store, _storage = _make_store()
        result = store.load_data("nonexistent-id")
        assert result is None

    def test_load_nonexistent_with_data_returns_none(self):
        store, _storage = _make_store()
        result = store.load_with_data("nonexistent-id")
        assert result is None

    def test_load_after_delete_returns_none(self):
        store, _storage = _make_store()
        att = _make_attachment()
        store.save(att, b"data")
        store.delete(att.id)
        assert store.load_metadata(att.id) is None

    def test_load_data_after_metadata_deleted_returns_none(self):
        store, storage = _make_store()
        att = _make_attachment()
        store.save(att, b"data")
        # manually delete metadata
        storage.delete(store._metadata_path(att.id))
        result = store.load_with_data(att.id)
        assert result is None


class TestAttachmentStoreDelete:
    def test_delete_removes_both(self):
        store, _storage = _make_store()
        att = _make_attachment()
        store.save(att, b"data")
        assert store.metadata_exists(att.id)
        assert store.binary_exists(att.id)
        store.delete(att.id)
        assert not store.metadata_exists(att.id)
        assert not store.binary_exists(att.id)

    def test_delete_nonexistent_returns_false(self):
        store, _storage = _make_store()
        result = store.delete("nonexistent")
        assert result is False

    def test_delete_twice_idempotent(self):
        store, _storage = _make_store()
        att = _make_attachment()
        store.save(att, b"data")
        store.delete(att.id)
        result = store.delete(att.id)
        assert result is False

    def test_delete_only_metadata(self):
        store, storage = _make_store()
        att = _make_attachment()
        store.save(att, b"data")
        storage.delete(store._binary_path(att.id))
        result = store.delete(att.id)
        assert result is True
        assert not store.metadata_exists(att.id)


class TestAttachmentStoreList:
    def test_list_empty(self):
        store, _storage = _make_store()
        ids = store.list_ids()
        assert ids == []

    def test_list_single(self):
        store, _storage = _make_store()
        att = _make_attachment()
        store.save(att, b"data")
        ids = store.list_ids()
        assert att.id in ids

    def test_list_multiple(self):
        store, _storage = _make_store()
        ids_expected = set()
        for _ in range(5):
            att = _make_attachment()
            store.save(att, b"data")
            ids_expected.add(att.id)
        ids_found = set(store.list_ids())
        assert ids_found == ids_expected

    def test_list_after_delete(self):
        store, _storage = _make_store()
        att1 = _make_attachment()
        att2 = _make_attachment()
        store.save(att1, b"data1")
        store.save(att2, b"data2")
        store.delete(att1.id)
        ids = store.list_ids()
        assert att1.id not in ids
        assert att2.id in ids

    def test_list_returns_sorted(self):
        store, _storage = _make_store()
        atts = [_make_attachment() for _ in range(3)]
        for att in atts:
            store.save(att, b"data")
        ids = store.list_ids()
        assert ids == sorted(ids)


class TestAttachmentStoreExistence:
    def test_metadata_exists(self):
        store, _storage = _make_store()
        att = _make_attachment()
        store.save(att, b"data")
        assert store.metadata_exists(att.id)

    def test_metadata_not_exists(self):
        store, _storage = _make_store()
        assert not store.metadata_exists("nonexistent")

    def test_binary_exists(self):
        store, _storage = _make_store()
        att = _make_attachment()
        store.save(att, b"data")
        assert store.binary_exists(att.id)

    def test_binary_not_exists(self):
        store, _storage = _make_store()
        assert not store.binary_exists("nonexistent")


class TestAttachmentStorePaths:
    def test_binary_path_format(self):
        att_id = str(uuid.uuid4())
        path = AttachmentStore._binary_path(att_id)
        assert path == f"attachments/{att_id}.bin"

    def test_metadata_path_format(self):
        att_id = str(uuid.uuid4())
        path = AttachmentStore._metadata_path(att_id)
        assert path == f"attachment-metadata/{att_id}.json"


class TestAttachmentStoreIsolation:
    def test_different_attachments_dont_interfere(self):
        store, _storage = _make_store()
        att1 = _make_attachment()
        att2 = _make_attachment()
        store.save(att1, b"data1")
        store.save(att2, b"data2")
        store.delete(att1.id)
        assert store.load_metadata(att2.id) is not None
        assert store.load_data(att2.id) == b"data2"

    def test_save_overwrites_existing(self):
        store, _storage = _make_store()
        att = _make_attachment()
        store.save(att, b"original")
        store.save(att, b"updated")
        assert store.load_data(att.id) == b"updated"
