# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

import uuid

from flask import Blueprint, request, jsonify
from services import platform
from palmshed_ai.conversations import ConversationStore, Conversation

conversations_bp = Blueprint("conversations", __name__)


def _get_store() -> ConversationStore:
    return ConversationStore(storage=platform.storage)


def _ensure_message_ids(messages: list[dict]) -> None:
    for msg in messages:
        if not msg.get("id"):
            msg["id"] = str(uuid.uuid4())


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

    try:
        conv = Conversation.from_dict(data)
    except (KeyError, ValueError) as e:
        return jsonify({"error": f"Invalid conversation data: {e}"}), 400

    if not data.get("title"):
        conv.title = _default_title(conv)

    created = store.create(conv)
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
    return jsonify(conv.to_dict())


@conversations_bp.route("/api/conversations/<conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id):
    store = _get_store()
    success = store.delete(conversation_id)
    if not success:
        return jsonify({"error": "Conversation not found"}), 404
    return "", 204


def _default_title(conv: Conversation) -> str:
    for msg in conv.messages:
        if msg.role == "user":
            text = msg.content.strip()
            if text:
                return text[:60]
    return "New conversation"
