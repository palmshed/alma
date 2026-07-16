# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
#
# This module defines the API routes for the Gemini AI Search application,
# including text generation, thinking mode, URL context, TTS, and image generation.

from flask import Blueprint, request, jsonify, send_file, after_this_request, Response
import os
import tempfile
import logging
from typing import Any, cast, Dict, Tuple, Union
from ..image_models import ImageStatus
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
        messages = data.get("messages")

        if not prompt and not messages:
            return jsonify({"error": "No prompt provided"}), 400

        if messages:
            response = ai.generate_chat(messages)
        else:
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
        messages = data.get("messages")

        if not prompt and not messages:
            return jsonify({"error": "No prompt provided"}), 400

        if messages:
            result = ai.generate_chat_with_thinking(messages)
        else:
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
        messages = data.get("messages")

        if not prompt and not messages:
            return jsonify({"error": "No prompt provided"}), 400

        if messages:
            response = ai.generate_chat_with_url_context(messages)
        else:
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
    data = cast(Dict[str, Any], request.get_json() or {})
    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    if len(prompt) > 5000:
        return jsonify({"error": "Prompt too long (max 5000 chars)"}), 400

    try:
        result = ai.generate_image(prompt)
    except Exception as e:
        return _error_response(e)

    if result.status == ImageStatus.OK:
        filepath = result.filepath

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

        mime_type = result.mime_type or "image/png"
        return send_file(filepath, mimetype=mime_type)

    status_map = {
        ImageStatus.QUOTA_EXCEEDED: 429,
        ImageStatus.UNAVAILABLE: 503,
        ImageStatus.UNSUPPORTED: 400,
        ImageStatus.FAILED: 500,
    }
    http_status = status_map.get(result.status, 500)
    return (
        jsonify(
            {
                "error": result.error,
                "provider": result.provider,
                "provider_status": result.status.value,
                "model": result.model,
            }
        ),
        http_status,
    )


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


@api_bp.route("/api/review-diff", methods=["POST"])
def review_diff() -> Union[Response, Tuple[Response, int]]:
    """Explain or review a pull request diff.

    Stable contract consumed by the diff product. Accepts a unified diff and
    an optional question, returns an AI-generated review.
    """
    try:
        data = cast(Dict[str, Any], request.get_json() or {})
        diff = data.get("diff", "").strip()
        question = data.get("question", "").strip() or "Explain this pull request."

        if not diff:
            return jsonify({"error": "No diff provided"}), 400

        if len(diff) > 50000:
            return jsonify({"error": "Diff too long (max 50000 chars)"}), 400

        prompt = (
            "You are a code review assistant. Given the following unified diff "
            "from a pull request, answer the request concisely and accurately.\n\n"
            f"Request: {question}\n\n"
            f"Diff:\n{diff}"
        )
        review = ai.generate_chat([{"role": "user", "content": prompt}])
        return jsonify({"review": review})

    except Exception as e:
        logging.error(f"Error in review_diff: {e}")
        return _error_response(e)


@api_bp.route("/api/health", methods=["GET"])
def health_check():
    """Health endpoint using PlatformManager."""
    from services import platform

    h = platform.health()
    return jsonify(h.to_dict())
