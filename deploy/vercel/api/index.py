import json

# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
#

import base64
import os
import sys
import tempfile
import mimetypes
from http.server import BaseHTTPRequestHandler
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend"))
from palmshed_ai import GeminiAI

# Load environment variables
load_dotenv()

ai = GeminiAI()


class Handler(BaseHTTPRequestHandler):
    """Vercel-compatible handler class for API endpoints."""

    def do_POST(self):
        """Handle POST requests."""
        # Get the path and query parameters
        path = self.path
        method = "generate"  # default

        if "?" in path:
            path_part, query_part = path.split("?", 1)
            # Parse query parameters
            from urllib.parse import parse_qs

            query_params = parse_qs(query_part)
            method = query_params.get("method", ["generate"])[0]

        # Read request body
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}

        # Route to appropriate handler
        if method == "generate":
            response = self._generate(data)
        elif method == "generate_with_thinking":
            response = self._generate_with_thinking(data)
        elif method == "generate_with_url_context":
            response = self._generate_with_url_context(data)
        elif method == "text_to_speech":
            response = self._text_to_speech(data)
        elif method == "generate_image":
            response = self._generate_image(data)
        else:
            response = {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Unknown method"}),
            }

        # Send response
        self.send_response(response["statusCode"])
        for header, value in response["headers"].items():
            self.send_header(header, value)
        self.end_headers()

        if "isBase64Encoded" in response and response["isBase64Encoded"]:
            self.wfile.write(base64.b64decode(response["body"]))
        else:
            self.wfile.write(response["body"].encode("utf-8"))

    def _generate(self, data):
        """Generate text response."""
        try:
            prompt = data.get("prompt", "").strip()

            if not prompt:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "No prompt provided"}),
                }

            if len(prompt) > 5000:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Prompt too long (max 5000 chars)"}),
                }

            response = ai.generate_text(prompt)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"response": response}),
            }

        except Exception as e:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": str(e)}),
            }

    def _generate_with_thinking(self, data):
        """Generate text response with thinking."""
        try:
            prompt = data.get("prompt", "").strip()

            if not prompt:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "No prompt provided"}),
                }

            if len(prompt) > 5000:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Prompt too long (max 5000 chars)"}),
                }

            result = ai.generate_text_with_thinking(prompt)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(result),
            }

        except Exception as e:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": str(e)}),
            }

    def _generate_with_url_context(self, data):
        """Generate text response with URL context."""
        try:
            prompt = data.get("prompt", "").strip()

            if not prompt:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "No prompt provided"}),
                }

            if len(prompt) > 5000:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Prompt too long (max 5000 chars)"}),
                }

            response = ai.generate_text_with_url_context(prompt)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"response": response}),
            }

        except Exception as e:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": str(e)}),
            }

    def _text_to_speech(self, data):
        """Convert text to speech."""
        try:
            text = data.get("text", "").strip()

            if not text:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "No text provided"}),
                }

            if len(text) > 1000:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Text too long (max 1000 chars)"}),
                }

            filepath = ai.text_to_speech(text)

            # Prevent path traversal
            if not os.path.commonpath(
                [os.path.abspath(tempfile.gettempdir()), os.path.abspath(filepath)]
            ) == os.path.abspath(tempfile.gettempdir()):
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Invalid file path"}),
                }

            # Read the file and return as base64
            with open(filepath, "rb") as f:
                audio_data = f.read()

            # Clean up the file
            try:
                os.remove(filepath)
            except OSError:
                pass

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "audio/mp3",
                    "Content-Disposition": 'attachment; filename="tts_audio.mp3"',
                },
                "body": base64.b64encode(audio_data).decode("utf-8"),
                "isBase64Encoded": True,
            }

        except Exception as e:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": str(e)}),
            }

    def _generate_image(self, data):
        """Generate image from text prompt."""
        try:
            prompt = data.get("prompt", "").strip()

            if not prompt:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "No prompt provided"}),
                }

            if len(prompt) > 5000:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Prompt too long (max 5000 chars)"}),
                }

            filepath = ai.generate_image(prompt)

            # Prevent path traversal
            if not os.path.commonpath(
                [os.path.abspath(tempfile.gettempdir()), os.path.abspath(filepath)]
            ) == os.path.abspath(tempfile.gettempdir()):
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Invalid file path"}),
                }

            # Detect mime type
            mime_type, _ = mimetypes.guess_type(filepath)
            if not mime_type:
                mime_type = "image/png"

            # Read the file and return as base64
            with open(filepath, "rb") as f:
                image_data = f.read()

            # Clean up the file
            try:
                os.remove(filepath)
            except OSError:
                pass

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": mime_type,
                    "Content-Disposition": 'inline; filename="generated_image.png"',
                },
                "body": base64.b64encode(image_data).decode("utf-8"),
                "isBase64Encoded": True,
            }

        except Exception as e:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": str(e)}),
            }
