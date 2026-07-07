# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

import logging
import uuid
from datetime import datetime, timezone

from flask import Blueprint, g, request, jsonify
from services import platform
from palmshed_ai.conversations import (
    AttachmentStore,
    ConversationStore,
    Conversation,
)

logger = logging.getLogger(__name__)


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


conversations_bp = Blueprint("conversations", __name__)


def _get_store() -> ConversationStore:
    return ConversationStore(storage=platform.storage, owner_id=g.client_id)


def _get_attachment_store() -> AttachmentStore:
    return AttachmentStore(storage=platform.storage)


def _ensure_message_ids(messages: list[dict]) -> None:
    for msg in messages:
        if not msg.get("id"):
            msg["id"] = str(uuid.uuid4())


def _populate_attachment_references(conversation_id: str, messages: list) -> None:
    """Store conversation_id and message_id on each referenced attachment.

    These are references only, not ownership — the attachment remains
    independently addressable and reusable.
    """
    att_store = _get_attachment_store()
    for msg in messages:
        attachments = (
            msg.attachments if hasattr(msg, "attachments") else msg.get("attachments")
        )
        if not attachments:
            continue
        message_id = msg.id if hasattr(msg, "id") else msg["id"]
        for ref in attachments:
            att_id = ref.get("id") if isinstance(ref, dict) else ref.id
            if att_id:
                att_store.update_metadata(
                    att_id,
                    {"conversation_id": conversation_id, "message_id": message_id},
                )


def _cleanup_attachments_for_conversation(
    conversation_id: str,
) -> list[str]:
    """Delete all attachments referenced by messages in a conversation.

    Returns a list of attachment IDs that could not be deleted.
    Does not raise — failures are logged and collected.
    """
    store = _get_store()
    conv = store.load(conversation_id)
    if conv is None:
        return []

    att_store = _get_attachment_store()
    failures: list[str] = []
    seen: set[str] = set()
    for msg in conv.messages:
        if not msg.attachments:
            continue
        for ref in msg.attachments:
            att_id = ref.get("id") if isinstance(ref, dict) else ref.id
            if att_id in seen:
                continue
            seen.add(att_id)
            try:
                if not att_store.delete(att_id):
                    logger.warning(
                        "Attachment %s not found during conversation %s cleanup",
                        att_id,
                        conversation_id,
                    )
            except Exception:
                logger.exception(
                    "Failed to delete attachment %s during conversation %s cleanup",
                    att_id,
                    conversation_id,
                )
                failures.append(att_id)
    return failures


@conversations_bp.route("/api/conversations", methods=["GET"])
def list_conversations():
    store = _get_store()
    entries = store.index_entries()
    return jsonify([e.to_dict() for e in entries])


@conversations_bp.route("/api/conversations/<conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    store = _get_store()
    conv = store.load(conversation_id)
    if conv is None:
        return jsonify({"error": "Conversation not found"}), 404
    return jsonify(conv.to_dict())


@conversations_bp.route("/api/conversations", methods=["POST"])
def create_conversation():
    store = _get_store()
    data = request.get_json(force=True) or {}

    if "messages" not in data:
        return jsonify({"error": "Missing required field: messages"}), 400
    if "mode" not in data or not data["mode"]:
        return jsonify({"error": "Missing required field: mode"}), 400

    if not data.get("id"):
        data["id"] = str(uuid.uuid4())

    _ensure_message_ids(data.get("messages", []))

    if "created_at" not in data:
        data["created_at"] = _now_utc()
    if "updated_at" not in data:
        data["updated_at"] = _now_utc()

    try:
        conv = Conversation.from_dict(data)
    except (KeyError, ValueError) as e:
        return jsonify({"error": f"Invalid conversation data: {e}"}), 400

    if not data.get("title"):
        conv.title = _default_title(conv)

    created = store.create(conv)

    _populate_attachment_references(created.id, created.messages)

    return jsonify(created.to_dict()), 201


@conversations_bp.route("/api/conversations/<conversation_id>", methods=["PUT"])
def update_conversation(conversation_id):
    store = _get_store()

    existing = store.load(conversation_id)
    if existing is None:
        return jsonify({"error": "Conversation not found"}), 404

    data = request.get_json(force=True) or {}

    if existing.title_is_manual and "title_is_manual" not in data:
        data["title"] = existing.title
        data["title_is_manual"] = True

    _ensure_message_ids(data.get("messages", []))

    data["id"] = conversation_id
    if "mode" not in data:
        return jsonify({"error": "Missing required field: mode"}), 400

    try:
        conv = Conversation.from_dict(data)
    except (KeyError, ValueError) as e:
        return jsonify({"error": f"Invalid conversation data: {e}"}), 400

    store.save(conv)

    _populate_attachment_references(conv.id, conv.messages)

    return jsonify(conv.to_dict())


@conversations_bp.route("/api/conversations/<conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id):
    failures = _cleanup_attachments_for_conversation(conversation_id)

    store = _get_store()
    success = store.delete(conversation_id)
    if not success:
        return jsonify({"error": "Conversation not found"}), 404

    if failures:
        logger.warning(
            "Conversation %s deleted but %d attachments could not be removed: %s",
            conversation_id,
            len(failures),
            ", ".join(failures),
        )

    return "", 204


def _default_title(conv: Conversation) -> str:
    for msg in conv.messages:
        if msg.role == "user":
            text = msg.content.strip()
            if text:
                return text[:60]
    return "New conversation"
