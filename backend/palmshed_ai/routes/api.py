# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
#
# This module defines the API routes for the Gemini AI Search application,
# including text generation, thinking mode, URL context, TTS, and image generation.

from flask import Blueprint, request, jsonify, send_file, after_this_request, Response
import os
import tempfile
import mimetypes
import logging
from typing import Any, cast, Dict, Tuple, Union
from ..sdk import GeminiAI


def _error_response(e: Exception) -> Tuple[Response, int]:
    msg = str(e)
    status = 429 if "429" in msg or "RESOURCE_EXHAUSTED" in msg else 500
    return jsonify({"error": msg}), status


def is_safe_path(base_path: str, target_path: str) -> bool:
    """Check if target_path is within base_path to prevent path traversal."""
    try:
        return os.path.commonpath(
            [os.path.abspath(base_path), os.path.abspath(target_path)]
        ) == os.path.abspath(base_path)
    except ValueError:
        return False


ai = GeminiAI()
api_bp = Blueprint("api", __name__)

# Create directories for temporary files
TEMP_AUDIO_DIR = os.path.join(tempfile.gettempdir(), "gemini_tts")
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

TEMP_IMAGE_DIR = os.path.join(tempfile.gettempdir(), "generated_images")
os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)


@api_bp.route("/api/generate", methods=["POST"])
def generate_response() -> Union[Response, Tuple[Response, int]]:
    try:
        data = cast(Dict[str, Any], request.get_json() or {})
        prompt = data.get("prompt", "").strip()

        if not prompt:
            return jsonify({"error": "No prompt provided"}), 400

        if len(prompt) > 5000:
            return jsonify({"error": "Prompt too long (max 5000 chars)"}), 400

        response = ai.generate_text(prompt)
        return jsonify({"response": response})

    except Exception as e:
        logging.error(f"Error in generate_response: {e}")
        return _error_response(e)


@api_bp.route("/api/generate-with-thinking", methods=["POST"])
def generate_response_with_thinking() -> Union[Response, Tuple[Response, int]]:
    try:
        data = cast(Dict[str, Any], request.get_json() or {})
        prompt = data.get("prompt", "").strip()

        if not prompt:
            return jsonify({"error": "No prompt provided"}), 400

        if len(prompt) > 5000:
            return jsonify({"error": "Prompt too long (max 5000 chars)"}), 400

        result = ai.generate_text_with_thinking(prompt)
        return jsonify(result)

    except Exception as e:
        logging.error(f"Error in generate_response_with_thinking: {e}")
        return _error_response(e)


@api_bp.route("/api/generate-with-url-context", methods=["POST"])
def generate_response_with_url_context() -> Union[Response, Tuple[Response, int]]:
    try:
        data = cast(Dict[str, Any], request.get_json() or {})
        prompt = data.get("prompt", "").strip()

        if not prompt:
            return jsonify({"error": "No prompt provided"}), 400

        if len(prompt) > 5000:
            return jsonify({"error": "Prompt too long (max 5000 chars)"}), 400

        response = ai.generate_text_with_url_context(prompt)
        return jsonify({"response": response})

    except Exception as e:
        logging.error(f"Error in generate_response_with_url_context: {e}")
        return _error_response(e)


@api_bp.route("/api/text-to-speech", methods=["POST"])
def text_to_speech() -> Union[Response, Tuple[Response, int]]:
    filepath = None
    try:
        data = cast(Dict[str, Any], request.get_json() or {})
        text = data.get("text", "").strip()

        if not text:
            return jsonify({"error": "No text provided"}), 400

        if len(text) > 1000:
            return jsonify({"error": "Text too long (max 1000 chars)"}), 400

        filepath = ai.text_to_speech(text)

        # Prevent path traversal
        if not is_safe_path(TEMP_AUDIO_DIR, filepath):
            try:
                os.unlink(filepath)
            except OSError:
                pass
            return jsonify({"error": "Invalid file path"}), 400

        @after_this_request
        def cleanup(response):
            try:
                os.unlink(filepath)
            except OSError:
                pass
            return response

        filename = os.path.basename(filepath)
        return send_file(
            filepath, mimetype="audio/mp3", as_attachment=True, download_name=filename
        )

    except Exception as e:
        logging.error(f"Error in text_to_speech: {e}")
        if filepath is not None:
            try:
                os.unlink(filepath)
            except OSError:
                pass
        return _error_response(e)


@api_bp.route("/api/generate-image", methods=["POST"])
def generate_image() -> Union[Response, Tuple[Response, int]]:
    filepath = None
    try:
        data = cast(Dict[str, Any], request.get_json() or {})
        prompt = data.get("prompt", "").strip()

        if not prompt:
            return jsonify({"error": "No prompt provided"}), 400

        if len(prompt) > 5000:
            return jsonify({"error": "Prompt too long (max 5000 chars)"}), 400

        filepath = ai.generate_image(prompt)

        # Prevent path traversal
        if not is_safe_path(TEMP_IMAGE_DIR, filepath):
            try:
                os.unlink(filepath)
            except OSError:
                pass
            return jsonify({"error": "Invalid file path"}), 400

        @after_this_request
        def cleanup(response):
            try:
                os.unlink(filepath)
            except OSError:
                pass
            return response

        # Detect mime type
        mime_type, _ = mimetypes.guess_type(filepath)
        if not mime_type:
            mime_type = "image/png"

        return send_file(filepath, mimetype=mime_type)

    except Exception as e:
        logging.error(f"Error in generate_image: {e}")
        if filepath is not None:
            try:
                os.unlink(filepath)
            except OSError:
                pass
        return _error_response(e)


@api_bp.route("/api/process-text-go", methods=["POST"])
def process_text_go() -> Union[Response, Tuple[Response, int]]:
    try:
        data = cast(Dict[str, Any], request.get_json() or {})
        text = data.get("text", "").strip()

        if not text:
            return jsonify({"error": "No text provided"}), 400

        if len(text) > 10000:  # Reasonable limit for text processing
            return jsonify({"error": "Text too long (max 10000 chars)"}), 400

        processed_text = ai.process_text_go(text)
        return jsonify({"processed_text": processed_text})

    except Exception as e:
        logging.error(f"Error in process_text_go: {e}")
        return jsonify({"error": "Internal server error"}), 500


@api_bp.route("/api/research", methods=["POST"])
def research_topic() -> Union[Response, Tuple[Response, int]]:
    try:
        data = cast(Dict[str, Any], request.get_json() or {})
        topic = data.get("topic", "").strip()

        if not topic:
            return jsonify({"error": "No topic provided"}), 400

        if len(topic) > 5000:
            return jsonify({"error": "Topic too long (max 5000 chars)"}), 400

        result = ai.research_topic(topic)
        return jsonify(result)

    except ValueError as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "access" in error_msg.lower():
            return (
                jsonify({"error": "Request rate limit exceeded or access denied"}),
                429,
            )
        elif "timeout" in error_msg.lower():
            return jsonify({"error": "Request timed out"}), 408
        else:
            return jsonify({"error": "Bad request"}), 400
    except Exception as e:
        logging.error(f"Error in research_topic: {e}")
        return jsonify({"error": "Internal server error"}), 500


@api_bp.route("/api/health", methods=["GET"])
def health_check():
    """Health endpoint including mail provider status."""
    from services.mail.config import MailConfig
    from services.mail.service import MailService

    config = MailConfig.from_env()
    mail_status = {"provider": config.provider, "from_email": config.from_email}

    valid, errors = config.is_valid()
    mail_status["config_valid"] = valid
    if errors:
        mail_status["config_errors"] = errors

    try:
        svc = MailService(config=config)
        health = svc.health()
        mail_status["provider"] = health.provider
        mail_status["queue_running"] = health.queue_running
        mail_status["queue_depth"] = health.queue_depth
        mail_status["templates_valid"] = health.templates_valid
        mail_status["template_count"] = health.template_count
    except Exception as exc:
        mail_status["error"] = str(exc)
        logging.warning("Mail service health check failed: %s", exc)

    return jsonify({"status": "ok", "mail": mail_status})
