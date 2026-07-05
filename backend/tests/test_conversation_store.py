# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

import uuid

from services.storage import StorageService, StorageConfig

from palmshed_ai.conversations import (
    Conversation,
    Message,
    ConversationStore,
    SCHEMA_VERSION,
)


def _make_conversation(overrides=None) -> Conversation:
    data = {
        "id": str(uuid.uuid4()),
        "title": "Test conversation",
        "mode": "chat",
        "created_at": "2026-07-05T12:00:00Z",
        "updated_at": "2026-07-05T12:00:00Z",
        "messages": [
            Message(
                id=str(uuid.uuid4()),
                role="user",
                timestamp="2026-07-05T12:00:00Z",
                content="Hello",
            ),
            Message(
                id=str(uuid.uuid4()),
                role="assistant",
                timestamp="2026-07-05T12:00:01Z",
                content="Hi there!",
            ),
        ],
    }
    if overrides:
        data.update(overrides)
    return Conversation(**data)


def _make_store() -> tuple[ConversationStore, StorageService]:
    config = StorageConfig(provider="mock", bucket="alma-test")
    storage = StorageService(config=config)
    store = ConversationStore(storage=storage)
    return store, storage


class TestConversationStoreCreate:
    def test_create_saves_conversation(self):
        store, _storage = _make_store()
        conv = _make_conversation()
        result = store.create(conv)
        assert result.id == conv.id
        loaded = store.load(conv.id)
        assert loaded is not None
        assert loaded.title == conv.title

    def test_create_adds_to_index(self):
        store, _storage = _make_store()
        conv = _make_conversation()
        store.create(conv)
        entries = store.index_entries()
        ids = [e.id for e in entries]
        assert conv.id in ids

    def test_create_sets_timestamps(self):
        store, _storage = _make_store()
        conv = _make_conversation()
        conv.created_at = ""
        conv.updated_at = ""
        result = store.create(conv)
        assert result.created_at != ""
        assert result.updated_at != ""
        assert result.created_at == result.updated_at

    def test_create_sets_schema_version(self):
        store, _storage = _make_store()
        conv = _make_conversation()
        conv.schema_version = 0
        result = store.create(conv)
        assert result.schema_version == SCHEMA_VERSION

    def test_exists_after_create(self):
        store, _storage = _make_store()
        conv = _make_conversation()
        store.create(conv)
        assert store.exists(conv.id) is True

    def test_create_multiple_conversations(self):
        store, _storage = _make_store()
        c1 = _make_conversation()
        c2 = _make_conversation()
        store.create(c1)
        store.create(c2)
        all_convs = store.load_all()
        assert len(all_convs) == 2


class TestConversationStoreSave:
    def test_save_updates_content(self):
        store, _storage = _make_store()
        conv = _make_conversation()
        store.create(conv)
        conv.messages[0].content = "Updated message"
        store.save(conv)
        loaded = store.load(conv.id)
        assert loaded is not None
        assert loaded.messages[0].content == "Updated message"

    def test_save_updates_timestamp(self):
        store, _storage = _make_store()
        conv = _make_conversation()
        store.create(conv)
        original = conv.updated_at
        conv.title = "New title"
        store.save(conv)
        assert conv.updated_at != original

    def test_save_updates_index(self):
        store, _storage = _make_store()
        conv = _make_conversation()
        store.create(conv)
        conv.title = "Renamed"
        store.save(conv)
        entries = store.index_entries()
        matching = [e for e in entries if e.id == conv.id]
        assert len(matching) == 1
        assert matching[0].title == "Renamed"


class TestConversationStoreLoad:
    def test_load_returns_conversation(self):
        store, _storage = _make_store()
        conv = _make_conversation()
        store.create(conv)
        loaded = store.load(conv.id)
        assert loaded is not None
        assert loaded.id == conv.id
        assert len(loaded.messages) == 2

    def test_load_nonexistent_returns_none(self):
        store, _storage = _make_store()
        result = store.load("nonexistent-id")
        assert result is None

    def test_load_all_returns_all(self):
        store, _storage = _make_store()
        convs = [_make_conversation() for _ in range(3)]
        for c in convs:
            store.create(c)
        loaded = store.load_all()
        assert len(loaded) == 3

    def test_load_all_empty(self):
        store, _storage = _make_store()
        loaded = store.load_all()
        assert loaded == []

    def test_load_all_after_delete(self):
        store, _storage = _make_store()
        c1 = _make_conversation()
        c2 = _make_conversation()
        store.create(c1)
        store.create(c2)
        store.delete(c1.id)
        loaded = store.load_all()
        assert len(loaded) == 1
        assert loaded[0].id == c2.id


class TestConversationStoreDelete:
    def test_delete_removes_conversation(self):
        store, _storage = _make_store()
        conv = _make_conversation()
        store.create(conv)
        result = store.delete(conv.id)
        assert result is True
        assert store.exists(conv.id) is False
        assert store.load(conv.id) is None

    def test_delete_removes_from_index(self):
        store, _storage = _make_store()
        conv = _make_conversation()
        store.create(conv)
        store.delete(conv.id)
        entries = store.index_entries()
        ids = [e.id for e in entries]
        assert conv.id not in ids

    def test_delete_nonexistent_returns_false(self):
        store, _storage = _make_store()
        result = store.delete("nonexistent-id")
        assert result is False

    def test_delete_file_removed_from_storage(self):
        store, storage = _make_store()
        conv = _make_conversation()
        store.create(conv)
        store.delete(conv.id)
        path = f"conversations/{conv.id}.json"
        assert storage.exists(path) is False


class TestConversationStoreOverwrite:
    def test_overwrite_preserves_messages(self):
        store, _storage = _make_store()
        conv = _make_conversation()
        store.create(conv)
        conv.title = "New title"
        store.save(conv)
        loaded = store.load(conv.id)
        assert loaded is not None
        assert loaded.title == "New title"
        assert len(loaded.messages) == 2
        assert loaded.messages[0].content == "Hello"

    def test_overwrite_index_updated(self):
        store, _storage = _make_store()
        conv = _make_conversation()
        store.create(conv)
        conv.title = "Renamed"
        store.save(conv)
        index_entry = [e for e in store.index_entries() if e.id == conv.id][0]
        assert index_entry.title == "Renamed"


class TestConversationStoreRestore:
    def test_load_all_returns_saved_conversations(self):
        store, _storage = _make_store()
        convs = [_make_conversation() for _ in range(5)]
        for c in convs:
            store.create(c)
        loaded = store.load_all()
        assert len(loaded) == 5
        loaded_ids = {c.id for c in loaded}
        expected_ids = {c.id for c in convs}
        assert loaded_ids == expected_ids

    def test_restore_after_reload(self):
        store, storage = _make_store()
        convs = [_make_conversation() for _ in range(3)]
        for c in convs:
            store.create(c)
        store2 = ConversationStore(storage=storage)
        loaded = store2.load_all()
        assert len(loaded) == 3


class TestConversationStoreCorruption:
    def test_corrupted_conversation_file_skipped_after_restart(self):
        store, storage = _make_store()
        conv = _make_conversation()
        store.create(conv)
        path = f"conversations/{conv.id}.json"
        storage.upload(path, b"not valid json", content_type="application/json")
        store2 = ConversationStore(storage=storage)
        loaded = store2.load(conv.id)
        assert loaded is None

    def test_corrupted_conversation_does_not_affect_others(self):
        store, storage = _make_store()
        c1 = _make_conversation()
        c2 = _make_conversation()
        store.create(c1)
        store.create(c2)
        path = f"conversations/{c1.id}.json"
        storage.upload(path, b"not valid json", content_type="application/json")
        store2 = ConversationStore(storage=storage)
        loaded = store2.load_all()
        ids = [c.id for c in loaded]
        assert c1.id not in ids
        assert c2.id in ids

    def test_missing_conversation_file_returns_none(self):
        store, _storage = _make_store()
        result = store.load("nonexistent-id")
        assert result is None

    def test_corrupted_index_recovers(self):
        store, storage = _make_store()
        conv = _make_conversation()
        store.create(conv)
        storage.upload(
            "conversations/index.json", b"corrupt", content_type="application/json"
        )
        store2 = ConversationStore(storage=storage)
        entries = store2.index_entries()
        assert entries == []

    def test_missing_index_creates_empty(self):
        store, storage = _make_store()
        entries = store.index_entries()
        assert entries == []


class TestConversationStoreAtomicity:
    def test_save_still_works_after_corrupted_file(self):
        store, storage = _make_store()
        conv = _make_conversation()
        store.create(conv)
        path = f"conversations/{conv.id}.json"
        storage.upload(path, b"garbage", content_type="application/json")
        c2 = _make_conversation()
        store.create(c2)
        assert store.exists(c2.id)

    def test_save_preserves_existing_index(self):
        store, _storage = _make_store()
        c1 = _make_conversation()
        c2 = _make_conversation()
        store.create(c1)
        store.create(c2)
        c1.title = "Updated title"
        store.save(c1)
        entries = store.index_entries()
        assert len(entries) == 2
        titles = {e.title for e in entries}
        assert "Updated title" in titles


class TestConversationStoreExists:
    def test_exists_returns_true(self):
        store, _storage = _make_store()
        conv = _make_conversation()
        store.create(conv)
        assert store.exists(conv.id) is True

    def test_exists_returns_false(self):
        store, _storage = _make_store()
        assert store.exists("nonexistent") is False

    def test_exists_after_delete(self):
        store, _storage = _make_store()
        conv = _make_conversation()
        store.create(conv)
        store.delete(conv.id)
        assert store.exists(conv.id) is False


class TestConversationStoreIndex:
    def test_index_entries_returned(self):
        store, _storage = _make_store()
        conv = _make_conversation(overrides={"title": "My Chat"})
        store.create(conv)
        entries = store.index_entries()
        assert len(entries) == 1
        assert entries[0].title == "My Chat"
        assert entries[0].mode == "chat"

    def test_list_ids(self):
        store, _storage = _make_store()
        c1 = _make_conversation()
        c2 = _make_conversation()
        store.create(c1)
        store.create(c2)
        ids = store.list_ids()
        assert len(ids) == 2
        assert c1.id in ids
        assert c2.id in ids

    def test_index_entries_order(self):
        store, _storage = _make_store()
        convs = [_make_conversation() for _ in range(5)]
        for c in convs:
            store.create(c)
        entries = store.index_entries()
        assert len(entries) == 5
        entry_ids = {e.id for e in entries}
        expected_ids = {c.id for c in convs}
        assert entry_ids == expected_ids
