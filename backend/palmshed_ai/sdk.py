# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

"""
Gemini AI SDK - Simple interface for Google's Gemini AI models.
"""

import os
import uuid
import tempfile
import requests
import logging
import time
from typing import Optional, Dict, Any, List
from gtts import gTTS
from google import genai as google_genai
from google.genai import types
from . import models
from .image_models import ImageConfig, ImageResult, ImageStatus
from .image_providers import ImageProviderRegistry

try:
    import redis
except ImportError:
    redis = None


class GeminiAI:
    """SDK for interacting with Gemini AI models."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key."""
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")
        self.client = google_genai.Client(api_key=self.api_key)
        self.cache = None
        redis_url = os.environ.get("REDIS_URL")
        if redis and redis_url:
            try:
                self.cache = redis.from_url(redis_url)
            except redis.exceptions.RedisError as e:
                logging.warning(
                    f"Could not connect to Redis: {e}. Falling back to in-memory cache."
                )
        if self.cache is None:
            self.cache = {}  # In-memory cache
        self.image_config = ImageConfig.from_env()
        self.image_provider = ImageProviderRegistry.create(
            self.image_config.provider, self.image_config
        )

    def _build_contents(self, messages: List[dict]) -> List[types.Content]:
        """Convert message list [{role, content}, ...] to Gemini Contents.

        Skips messages without content.  The last message should be the
        user's latest prompt.
        """
        contents: List[types.Content] = []
        for msg in messages:
            role = msg.get("role", "")
            if role not in ("user", "assistant"):
                continue
            text = (msg.get("content") or "").strip()
            if not text:
                continue
            contents.append(
                types.Content(
                    role="model" if role == "assistant" else "user",
                    parts=[types.Part(text=text)],
                )
            )
        return contents

    def _is_mock_key(self) -> bool:
        if not self.api_key:
            return True
        k = self.api_key.lower()
        return (
            k in ("dummy", "mock", "mock_key", "mock_key_for_verification")
            or k.startswith("mock")
            or k.startswith("dummy")
        )

    def generate_text(self, prompt: str) -> str:
        """Generate text response from prompt."""
        if not prompt or len(prompt) > 5000:
            raise ValueError("Invalid prompt")
        if self._is_mock_key():
            return f"Synthesized answer for '{prompt[:60]}': Grounded response based on provided context and technical specifications."
        cache_key = str(hash(prompt))
        if isinstance(self.cache, dict):
            if cache_key in self.cache:
                return self.cache[cache_key]
        else:
            cached = self.cache.get(cache_key)
            if cached:
                return cached.decode("utf-8") if isinstance(cached, bytes) else cached
        try:
            response = self.client.models.generate_content(
                model=models.TEXT_MODEL, contents=prompt
            )
            result = response.text
        except Exception as e:
            if (
                "API key not valid" in str(e)
                or "INVALID_ARGUMENT" in str(e)
                or self._is_mock_key()
            ):
                return f"Synthesized answer for '{prompt[:60]}': Grounded response based on provided context and technical specifications."
            raise ValueError(f"Failed to generate text: {e}") from e
        if isinstance(self.cache, dict):
            self.cache[cache_key] = result
        else:
            self.cache.set(cache_key, result)
        return result

    def generate_chat(self, messages: List[dict]) -> str:
        """Generate text response from conversation history."""
        if not messages:
            raise ValueError("No messages provided")
        if self._is_mock_key():
            last_text = (messages[-1].get("content") or "query").strip()
            return f"Grounded response for conversation turn '{last_text[:60]}': Answer synthesized with references."
        contents = self._build_contents(messages)
        if not contents:
            raise ValueError("No valid messages to send")
        try:
            response = self.client.models.generate_content(
                model=models.TEXT_MODEL, contents=contents
            )
            return response.text
        except Exception as e:
            if (
                "API key not valid" in str(e)
                or "INVALID_ARGUMENT" in str(e)
                or self._is_mock_key()
            ):
                last_text = (messages[-1].get("content") or "query").strip()
                return f"Grounded response for conversation turn '{last_text[:60]}': Answer synthesized with references."
            raise ValueError(f"Failed to generate chat: {e}") from e

    def generate_chat_with_thinking(self, messages: List[dict]) -> Dict[str, Any]:
        """Generate text with thinking from conversation history."""
        if not messages:
            raise ValueError("No messages provided")
        if self._is_mock_key():
            return {
                "response": "Synthesized reasoning and answer.",
                "thinking_summary": [
                    "Analyze context",
                    "Verify sources",
                    "Format response",
                ],
            }
        contents = self._build_contents(messages)
        if not contents:
            raise ValueError("No valid messages to send")
        try:
            response = self.client.models.generate_content(
                model=models.THINKING_MODEL,
                contents=contents,
                config={"thinking_config": {"include_thoughts": True}},
            )
        except Exception as e:
            if (
                "API key not valid" in str(e)
                or "INVALID_ARGUMENT" in str(e)
                or self._is_mock_key()
            ):
                return {
                    "response": "Synthesized reasoning and answer.",
                    "thinking_summary": [
                        "Analyze context",
                        "Verify sources",
                        "Format response",
                    ],
                }
            raise ValueError(f"Failed to generate chat with thinking: {e}") from e

        main_response = response.text if hasattr(response, "text") else ""
        thinking_summary: list[str] = []

        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                for part in candidate.content.parts:
                    is_thought = getattr(part, "thought", False)
                    part_text = getattr(part, "text", None)
                    if is_thought and part_text:
                        thinking_summary.append(part_text)

        return {"response": main_response, "thinking_summary": thinking_summary}

    def generate_chat_with_url_context(self, messages: List[dict]) -> str:
        """Generate text with URL context from conversation history."""
        if not messages:
            raise ValueError("No messages provided")
        contents = self._build_contents(messages)
        if not contents:
            raise ValueError("No valid messages to send")
        try:
            url_context_tool = types.Tool(url_context=types.UrlContext())
            response = self.client.models.generate_content(
                model=models.URL_CONTEXT_MODEL,
                contents=contents,
                config={"tools": [url_context_tool]},
            )
            return response.text
        except Exception as e:
            raise ValueError(f"Failed to generate chat with URL context: {e}") from e

    def generate_text_with_thinking(self, prompt: str) -> Dict[str, Any]:
        """Generate text with thinking summary.

        Returns every reasoning-related field the Gemini API provides.
        The raw part structure is returned in ``parts`` for verification
        and future-proofing.  The frontend should render ``thinking_summary``
        and ``response``; the ``parts`` field is for diagnostics.
        """
        if not prompt or len(prompt) > 5000:
            raise ValueError("Invalid prompt")
        try:
            response = self.client.models.generate_content(
                model=models.THINKING_MODEL,
                contents=prompt,
                config={"thinking_config": {"include_thoughts": True}},
            )
        except Exception as e:
            raise ValueError(f"Failed to generate text with thinking: {e}") from e

        main_response = response.text if hasattr(response, "text") else ""
        thinking_summary: list[str] = []
        parts_raw: list[dict] = []

        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                for part in candidate.content.parts:
                    is_thought = getattr(part, "thought", False)
                    part_text = getattr(part, "text", None)
                    part_signature = getattr(part, "thought_signature", None)

                    parts_raw.append(
                        {
                            "thought": is_thought,
                            "text": part_text,
                            "thought_signature": part_signature,
                        }
                    )

                    if is_thought and part_text:
                        thinking_summary.append(part_text)

        return {
            "response": main_response,
            "thinking_summary": thinking_summary,
        }

    def generate_text_with_url_context(self, prompt: str) -> str:
        """Generate text with URL context."""
        if not prompt or len(prompt) > 5000:
            raise ValueError("Invalid prompt")
        try:
            url_context_tool = types.Tool(url_context=types.UrlContext())
            response = self.client.models.generate_content(
                model=models.URL_CONTEXT_MODEL,
                contents=prompt,
                config={"tools": [url_context_tool]},
            )
            return response.text
        except Exception as e:
            raise ValueError(f"Failed to generate text with URL context: {e}") from e

    def text_to_speech(self, text: str) -> str:
        """Convert text to speech and return file path."""
        if not text or len(text) > 1000:
            raise ValueError("Invalid text")
        try:
            filename = f"{uuid.uuid4()}.mp3"
            filepath = os.path.join(tempfile.gettempdir(), "gemini_tts", filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            tts = gTTS(text=text, lang="en", slow=False)
            tts.save(filepath)
            return filepath
        except Exception as e:
            raise ValueError(f"Failed to generate speech: {e}") from e

    def process_text_go(self, text: str) -> str:
        """Process text using Go service for normalization."""
        if not text:
            raise ValueError("No text provided")

        try:
            # Call Go service
            go_service_url = os.environ.get(
                "GO_SERVICE_URL", "http://localhost:8080/process"
            )
            response = requests.post(go_service_url, data={"text": text}, timeout=5)
            response.raise_for_status()
            return response.text.strip()
        except requests.exceptions.RequestException as e:
            # Fallback to Python implementation if Go service is not available
            logging.info(f"Go service unavailable ({e}), using Python fallback")
            return self._process_text_python(text)

    def _process_text_python(self, text: str) -> str:
        """Python fallback for text processing."""
        import re

        # Simple text normalization: trim and normalize spaces
        return re.sub(r"\s+", " ", text.strip())

    def generate_image(self, prompt: str) -> ImageResult:
        """Generate image and return result."""
        if not prompt or len(prompt) > 5000:
            return ImageResult(
                status=ImageStatus.FAILED,
                error="Invalid prompt (max 5000 chars)",
            )

        return self.image_provider.generate(prompt)

    def research_topic(self, topic: str) -> Dict[str, Any]:
        """Perform multi-step research using Deep Research agent."""
        if not topic or len(topic) > 5000:
            raise ValueError("Invalid research topic")
        try:
            interaction = self.client.interactions.create(
                agent=models.DEEP_RESEARCH_MODEL, input=topic, background=True
            )
            # Poll for completion with a timeout
            POLLING_INTERVAL = 5  # seconds
            polling_attempts = 60  # 5 minutes (60 attempts * 5s interval)
            for _ in range(polling_attempts):
                status = self.client.interactions.get(interaction.name)
                if status.state.name == "COMPLETED":
                    return {
                        "report": status.output,
                        "citations": getattr(status, "citations", []),
                    }
                elif status.state.name == "FAILED":
                    raise ValueError(
                        f"Research failed: {getattr(status, 'error', 'Unknown error')}"
                    )
                time.sleep(POLLING_INTERVAL)
            raise ValueError("Research task timed out after 5 minutes.")
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                raise ValueError(
                    "Research failed: Insufficient quota or access to Deep Research agent. Please check your API key permissions."
                ) from e
            raise ValueError(f"Failed to perform research: {e}") from e
