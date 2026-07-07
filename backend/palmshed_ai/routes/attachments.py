# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

import hashlib
import uuid
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, send_file
from services import platform

from palmshed_ai.conversations import Attachment, AttachmentStore

import io

attachments_bp = Blueprint("attachments", __name__)

SUPPORTED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "application/pdf",
    "text/plain",
    "text/markdown",
}

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _get_store() -> AttachmentStore:
    return AttachmentStore(storage=platform.storage)


@attachments_bp.route("/api/attachments", methods=["POST"])
def upload_attachment():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "" or not file.filename:
        return jsonify({"error": "No file selected"}), 400

    data = file.read()
    if len(data) == 0:
        return jsonify({"error": "Empty file"}), 400

    if len(data) > MAX_UPLOAD_SIZE:
        return jsonify(
            {"error": f"File too large ({len(data)} bytes); max is {MAX_UPLOAD_SIZE}"}
        ), 413

    mime_type = file.content_type or "application/octet-stream"
    if mime_type not in SUPPORTED_MIME_TYPES:
        return jsonify({"error": f"Unsupported file type: {mime_type}"}), 415

    checksum = hashlib.sha256(data).hexdigest()
    attachment_id = str(uuid.uuid4())
    storage_key = f"attachments/{attachment_id}.bin"

    attachment = Attachment(
        id=attachment_id,
        filename=file.filename,
        mime_type=mime_type,
        size=len(data),
        checksum=checksum,
        storage_key=storage_key,
        created_at=_now_utc(),
    )

    store = _get_store()
    store.save(attachment, data)

    return jsonify(attachment.to_dict()), 201


@attachments_bp.route("/api/attachments/<attachment_id>", methods=["GET"])
def download_attachment(attachment_id):
    store = _get_store()
    result = store.load_with_data(attachment_id)
    if result is None:
        return jsonify({"error": "Attachment not found"}), 404

    attachment, data = result
    return send_file(
        io.BytesIO(data),
        mimetype=attachment.mime_type,
        as_attachment=False,
        download_name=attachment.filename,
    )


@attachments_bp.route("/api/attachments/<attachment_id>/metadata", methods=["GET"])
def get_attachment_metadata(attachment_id):
    store = _get_store()
    attachment = store.load_metadata(attachment_id)
    if attachment is None:
        return jsonify({"error": "Attachment not found"}), 404

    return jsonify(attachment.to_dict())


@attachments_bp.route("/api/attachments/<attachment_id>", methods=["DELETE"])
def delete_attachment(attachment_id):
    store = _get_store()
    success = store.delete(attachment_id)
    if not success:
        return jsonify({"error": "Attachment not found"}), 404
    return "", 204
