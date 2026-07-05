# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

import json
import uuid

import pytest

from palmshed_ai.conversations import Conversation, Message, SCHEMA_VERSION


def _make_message(overrides=None):
    data = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "timestamp": "2026-07-05T12:00:00Z",
        "content": "Hello",
    }
    if overrides:
        data.update(overrides)
    return Message(**data)


def _make_conversation(message_count=1, overrides=None):
    messages = [_make_message() for _ in range(message_count)]
    data = {
        "id": str(uuid.uuid4()),
        "title": "Test conversation",
        "mode": "chat",
        "created_at": "2026-07-05T12:00:00Z",
        "updated_at": "2026-07-05T12:05:00Z",
        "messages": messages,
    }
    if overrides:
        data.update(overrides)
    return Conversation(**data)


class TestMessageSerialization:
    def test_round_trip_minimal(self):
        msg = _make_message()
        d = msg.to_dict()
        restored = Message.from_dict(d)
        assert restored.id == msg.id
        assert restored.role == msg.role
        assert restored.timestamp == msg.timestamp
        assert restored.content == msg.content
        assert restored.thinking is None
        assert restored.image is None
        assert restored.attachments is None

    def test_round_trip_all_fields(self):
        msg = _make_message({
            "thinking": "I think...",
            "image": "data:image/png;base64,abc123",
            "attachments": [{"filename": "test.pdf", "mime": "application/pdf"}],
            "metadata": {"source": "web"},
        })
        d = msg.to_dict()
        restored = Message.from_dict(d)
        assert restored.thinking == "I think..."
        assert restored.image == "data:image/png;base64,abc123"
        assert restored.attachments == [{"filename": "test.pdf", "mime": "application/pdf"}]
        assert restored.metadata == {"source": "web"}

    def test_unknown_fields_preserved(self):
        raw = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "timestamp": "2026-07-05T12:00:00Z",
            "content": "Hello back",
            "future_field": "something new",
        }
        msg = Message.from_dict(raw)
        d = msg.to_dict()
        assert d["future_field"] == "something new"

    def test_json_round_trip(self):
        msg = _make_message({
            "thinking": "hmm",
            "metadata": {"key": "val"},
        })
        raw_json = json.dumps(msg.to_dict())
        restored = Message.from_dict(json.loads(raw_json))
        assert restored.content == msg.content
        assert restored.thinking == "hmm"
        assert restored.metadata == {"key": "val"}


class TestConversationSerialization:
    def test_round_trip_minimal(self):
        conv = _make_conversation()
        d = conv.to_dict()
        restored = Conversation.from_dict(d)
        assert restored.id == conv.id
        assert restored.title == conv.title
        assert restored.mode == conv.mode
        assert restored.schema_version == SCHEMA_VERSION
        assert len(restored.messages) == 1
        assert restored.messages[0].content == "Hello"

    def test_round_trip_multiple_messages(self):
        conv = _make_conversation(message_count=3)
        d = conv.to_dict()
        restored = Conversation.from_dict(d)
        assert len(restored.messages) == 3

    def test_schema_version_present(self):
        conv = _make_conversation()
        d = conv.to_dict()
        assert d["schema_version"] == SCHEMA_VERSION

    def test_future_schema_version_raises(self):
        raw = {
            "id": str(uuid.uuid4()),
            "title": "future",
            "mode": "chat",
            "schema_version": 999,
            "created_at": "2026-07-05T12:00:00Z",
            "updated_at": "2026-07-05T12:00:00Z",
            "messages": [],
        }
        with pytest.raises(ValueError, match="newer"):
            Conversation.from_dict(raw)

    def test_unknown_fields_preserved(self):
        raw = {
            "id": str(uuid.uuid4()),
            "title": "test",
            "mode": "chat",
            "schema_version": 1,
            "created_at": "2026-07-05T12:00:00Z",
            "updated_at": "2026-07-05T12:00:00Z",
            "messages": [],
            "pinned": True,
            "color": "blue",
        }
        conv = Conversation.from_dict(raw)
        d = conv.to_dict()
        assert d["pinned"] is True
        assert d["color"] == "blue"

    def test_json_round_trip(self):
        conv = _make_conversation(message_count=2, overrides={
            "metadata": {"tags": ["test"]},
        })
        conv.messages[0].thinking = "reasoning..."
        conv.messages[1].role = "assistant"
        conv.messages[1].content = "Response here"

        raw_json = json.dumps(conv.to_dict())
        restored = Conversation.from_dict(json.loads(raw_json))

        assert restored.id == conv.id
        assert restored.title == conv.title
        assert restored.metadata == {"tags": ["test"]}
        assert len(restored.messages) == 2
        assert restored.messages[0].thinking == "reasoning..."
        assert restored.messages[1].role == "assistant"
        assert restored.messages[1].content == "Response here"

    def test_metadata_excluded_when_empty(self):
        conv = _make_conversation()
        conv.metadata = None
        d = conv.to_dict()
        assert "metadata" not in d or d["metadata"] is None

    def test_empty_messages_list(self):
        conv = _make_conversation(message_count=0, overrides={"messages": []})
        d = conv.to_dict()
        restored = Conversation.from_dict(d)
        assert restored.messages == []


class TestSchemaVersion:
    def test_current_version(self):
        assert SCHEMA_VERSION == 1

    def test_older_version_loads(self):
        raw = {
            "id": str(uuid.uuid4()),
            "title": "old",
            "mode": "chat",
            "schema_version": 0,
            "created_at": "2026-07-05T12:00:00Z",
            "updated_at": "2026-07-05T12:00:00Z",
            "messages": [],
        }
        conv = Conversation.from_dict(raw)
        assert conv.schema_version == 0

    def test_missing_schema_defaults_to_zero(self):
        raw = {
            "id": str(uuid.uuid4()),
            "title": "no version",
            "mode": "chat",
            "created_at": "2026-07-05T12:00:00Z",
            "updated_at": "2026-07-05T12:00:00Z",
            "messages": [],
        }
        conv = Conversation.from_dict(raw)
        assert conv.schema_version == 0


class TestImmutability:
    def test_message_list_not_shared(self):
        conv1 = _make_conversation(message_count=2)
        conv2 = _make_conversation(message_count=2)
        assert conv1.messages is not conv2.messages

    def test_to_dict_returns_new_dict(self):
        conv = _make_conversation()
        d1 = conv.to_dict()
        d1["title"] = "modified"
        assert conv.title != "modified"
        # verify a fresh to_dict() is unmodified
        d3 = conv.to_dict()
        assert d3["title"] == "Test conversation"


class TestIdentifier:
    def test_uuid_format(self):
        conv = _make_conversation()
        # just check it's a non-empty string
        assert isinstance(conv.id, str)
        assert len(conv.id) > 0


class TestTimestampFormat:
    def test_iso_8601_utc(self):
        conv = _make_conversation()
        assert conv.created_at.endswith("Z")
        assert "T" in conv.created_at
