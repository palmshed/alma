# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

from flask import Blueprint, request, jsonify
from services import platform
from palmshed_ai.conversations import ConversationStore, Conversation

conversations_bp = Blueprint("conversations", __name__)


def _get_store() -> ConversationStore:
    return ConversationStore(storage=platform.storage)


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
    conv = Conversation.from_dict(data)
    created = store.create(conv)
    return jsonify(created.to_dict()), 201


@conversations_bp.route("/api/conversations/<conversation_id>", methods=["PUT"])
def update_conversation(conversation_id):
    store = _get_store()
    data = request.get_json(force=True) or {}
    conv = Conversation.from_dict(data)
    if conv.id != conversation_id:
        return jsonify({"error": "Conversation ID mismatch"}), 400
    store.save(conv)
    return jsonify(conv.to_dict())


@conversations_bp.route("/api/conversations/<conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id):
    store = _get_store()
    success = store.delete(conversation_id)
    if not success:
        return jsonify({"error": "Conversation not found"}), 404
    return jsonify({"status": "deleted"})
