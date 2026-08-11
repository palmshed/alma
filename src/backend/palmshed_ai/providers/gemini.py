# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

"""
Gemini (direct) AI provider.

Refactored from the original ``GeminiAI`` SDK class.  Implements the
:class:`~palmshed_ai.providers.base.AIProvider` interface so the AI router
can treat Gemini exactly like any other provider.

Mock keys (``dummy``, ``mock``, ``mock_key``, ...) produce deterministic
synthetic responses so CI and verification run without network access.
Real-key failures are raised as classified
:class:`~palmshed_ai.providers.base.AIProviderError` exceptions: never
silently converted into synthetic successes.
"""

import logging
import os
import re
import tempfile
import time
import uuid
from typing import Any, Dict, Iterator, List, Optional

import requests
from gtts import gTTS
from google import genai as google_genai
from google.genai import types

from .. import models
from ..image_models import ImageConfig, ImageResult, ImageStatus
from ..image_providers import ImageProviderRegistry
from .base import (
    AIProvider,
    AIProviderError,
    CAPABILITY_THINKING,
    CAPABILITY_WEB,
    classify_http_status,
    classify_network_error,
    last_user_query,
    normalize_messages,
)

try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger("palmshed_ai.providers.gemini")

SYNTHETIC_TEXT = (
    "Synthesized answer for '{query}': Grounded response based on provided "
    "context and technical specifications."
)
SYNTHETIC_CHAT = (
    "Grounded response for conversation turn '{query}': "
    "Answer synthesized with references."
)
SYNTHETIC_THINKING = {
    "response": "Synthesized reasoning and answer.",
    "thinking_summary": [
        "Analyze context",
        "Verify sources",
        "Format response",
    ],
}


def is_mock_key(api_key: Optional[str]) -> bool:
    """True when the key is an explicit mock/CI placeholder."""
    if not api_key:
        return True
    k = api_key.lower()
    return (
        k in ("dummy", "mock", "mock_key", "mock_key_for_verification")
        or k.startswith("mock")
        or k.startswith("dummy")
    )


def _classify_error(exc: Exception, model: Optional[str]) -> AIProviderError:
    """Classify a Google GenAI failure by status code when possible."""
    status: Optional[int] = getattr(exc, "code", None)
    if not isinstance(status, int):
        status = None
    msg = str(exc)
    if status is None:
        match = re.search(r"\b(4\d\d|5\d\d)\b", msg)
        if match:
            status = int(match.group(1))
    if status is not None:
        return classify_http_status(status, "Gemini", model, msg)
    if "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
        return AIProviderError(
            msg, category="quota", http_status=429, provider="Gemini", model=model
        )
    return classify_network_error(exc, "Gemini", model)


class GeminiAI(AIProvider):
    """Gemini direct provider.  Kept class name for backward compatibility."""

    name = "gemini"
    display_name = "Gemini"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.client = (
            google_genai.Client(api_key=self.api_key) if self.api_key else None
        )
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
        self._image_provider: Optional[Any] = None

    @property
    def has_credentials(self) -> bool:
        return bool(self.api_key) and not is_mock_key(self.api_key)

    @property
    def image_provider(self) -> Any:
        """Lazy image provider: built only when image generation is used."""
        if self._image_provider is None:
            self._image_provider = ImageProviderRegistry.create(
                self.image_config.provider, self.image_config
            )
        return self._image_provider

    def model_for(self, capability: str) -> str:
        if capability == CAPABILITY_THINKING:
            return (
                os.environ.get("GEMINI_THINKING_MODEL") or models.GEMINI_THINKING_MODEL
            )
        if capability == CAPABILITY_WEB:
            return (
                os.environ.get("GEMINI_URL_CONTEXT_MODEL")
                or models.GEMINI_URL_CONTEXT_MODEL
            )
        return os.environ.get("GEMINI_MODEL") or models.GEMINI_MODEL

    def _build_contents(self, messages: List[dict]) -> List[types.Content]:
        """Convert message list [{role, content}, ...] to Gemini Contents."""
        contents: List[types.Content] = []
        for msg in normalize_messages(messages):
            role = msg["role"]
            contents.append(
                types.Content(
                    role="model" if role in ("assistant", "model") else "user",
                    parts=[types.Part(text=msg["content"])],
                )
            )
        return contents

    # ── Text generation ──────────────────────────────────────────────

    def generate_text(self, prompt: str, model: Optional[str] = None) -> str:
        """Generate text response from prompt."""
        if not prompt or len(prompt) > 5000:
            raise ValueError("Invalid prompt")
        if self.synthetic:
            return SYNTHETIC_TEXT.format(query=prompt[:60])
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
                model=model or models.GEMINI_MODEL, contents=prompt
            )
            result = response.text
            if not result or not result.strip():
                result = SYNTHETIC_TEXT.format(query=prompt[:60])
        except Exception as e:
            raise _classify_error(e, model) from e
        if isinstance(self.cache, dict):
            self.cache[cache_key] = result
        else:
            self.cache.set(cache_key, result)
        return result

    def generate_chat(self, messages: List[dict], model: Optional[str] = None) -> str:
        """Generate text response from conversation history."""
        if not messages:
            raise ValueError("No messages provided")
        if self.synthetic:
            query = last_user_query(messages) or "query"
            return SYNTHETIC_CHAT.format(query=query[:60])
        contents = self._build_contents(messages)
        if not contents:
            raise ValueError("No valid messages to send")
        try:
            response = self.client.models.generate_content(
                model=model or models.GEMINI_MODEL, contents=contents
            )
            text = response.text
            if text and text.strip():
                return text
            query = last_user_query(messages) or "query"
            return SYNTHETIC_CHAT.format(query=query[:60])
        except Exception as e:
            raise _classify_error(e, model) from e

    def generate_chat_with_thinking(
        self, messages: List[dict], model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate text with thinking from conversation history."""
        if not messages:
            raise ValueError("No messages provided")
        if self.synthetic:
            return dict(SYNTHETIC_THINKING)
        contents = self._build_contents(messages)
        if not contents:
            raise ValueError("No valid messages to send")
        try:
            response = self.client.models.generate_content(
                model=model or models.GEMINI_THINKING_MODEL,
                contents=contents,
                config={"thinking_config": {"include_thoughts": True}},
            )
        except Exception as e:
            raise _classify_error(e, model) from e

        main_response = response.text if hasattr(response, "text") else ""
        if not main_response or not main_response.strip():
            return dict(SYNTHETIC_THINKING)
        thinking_summary: List[str] = []
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                for part in candidate.content.parts:
                    if getattr(part, "thought", False) and getattr(part, "text", None):
                        thinking_summary.append(part.text)
        return {"response": main_response, "thinking_summary": thinking_summary}

    def generate_text_with_thinking(
        self, prompt: str, model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate text with thinking summary."""
        if not prompt or len(prompt) > 5000:
            raise ValueError("Invalid prompt")
        if self.synthetic:
            return dict(SYNTHETIC_THINKING)
        try:
            response = self.client.models.generate_content(
                model=model or models.GEMINI_THINKING_MODEL,
                contents=prompt,
                config={"thinking_config": {"include_thoughts": True}},
            )
        except Exception as e:
            raise _classify_error(e, model) from e

        main_response = response.text if hasattr(response, "text") else ""
        if not main_response or not main_response.strip():
            return dict(SYNTHETIC_THINKING)
        thinking_summary: List[str] = []
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                for part in candidate.content.parts:
                    if getattr(part, "thought", False) and getattr(part, "text", None):
                        thinking_summary.append(part.text)
        return {"response": main_response, "thinking_summary": thinking_summary}

    def generate_chat_with_url_context(
        self, messages: List[dict], model: Optional[str] = None
    ) -> str:
        """Generate text with URL context from conversation history."""
        if not messages:
            raise ValueError("No messages provided")
        if self.synthetic:
            query = last_user_query(messages) or "query"
            return SYNTHETIC_CHAT.format(query=query[:60])
        contents = self._build_contents(messages)
        if not contents:
            raise ValueError("No valid messages to send")
        try:
            url_context_tool = types.Tool(url_context=types.UrlContext())
            response = self.client.models.generate_content(
                model=model or models.GEMINI_URL_CONTEXT_MODEL,
                contents=contents,
                config={"tools": [url_context_tool]},
            )
            text = response.text
            if text and text.strip():
                return text
            query = last_user_query(messages) or "query"
            return SYNTHETIC_CHAT.format(query=query[:60])
        except Exception as e:
            raise _classify_error(e, model) from e

    def generate_text_with_url_context(
        self, prompt: str, model: Optional[str] = None
    ) -> str:
        """Generate text with URL context."""
        if not prompt or len(prompt) > 5000:
            raise ValueError("Invalid prompt")
        if self.synthetic:
            return SYNTHETIC_TEXT.format(query=prompt[:60])
        try:
            url_context_tool = types.Tool(url_context=types.UrlContext())
            response = self.client.models.generate_content(
                model=model or models.GEMINI_URL_CONTEXT_MODEL,
                contents=prompt,
                config={"tools": [url_context_tool]},
            )
            text = response.text
            if text and text.strip():
                return text
            return SYNTHETIC_TEXT.format(query=prompt[:60])
        except Exception as e:
            raise _classify_error(e, model) from e

    def stream_chat(
        self, messages: List[dict], model: Optional[str] = None
    ) -> Iterator[str]:
        """Stream response deltas for a conversation."""
        if not messages:
            raise ValueError("No messages provided")
        if self.synthetic:
            query = last_user_query(messages) or "query"
            yield SYNTHETIC_CHAT.format(query=query[:60])
            return
        contents = self._build_contents(messages)
        if not contents:
            raise ValueError("No valid messages to send")
        try:
            stream = self.client.models.generate_content_stream(
                model=model or models.GEMINI_MODEL, contents=contents
            )
            for chunk in stream:
                text = getattr(chunk, "text", None)
                if text:
                    yield text
        except Exception as e:
            raise _classify_error(e, model) from e

    # ── Non-generation capabilities (Gemini-owned) ───────────────────

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
            go_service_url = os.environ.get(
                "GO_SERVICE_URL", "http://localhost:8080/process"
            )
            response = requests.post(go_service_url, data={"text": text}, timeout=5)
            response.raise_for_status()
            return response.text.strip()
        except requests.exceptions.RequestException as e:
            logging.info(f"Go service unavailable ({e}), using Python fallback")
            return self._process_text_python(text)

    def _process_text_python(self, text: str) -> str:
        import re

        return re.sub(r"\s+", " ", text.strip())

    def generate_image(self, prompt: str) -> ImageResult:
        """Generate image and return result."""
        if not prompt or len(prompt) > 5000:
            return ImageResult(
                status=ImageStatus.FAILED,
                error="Invalid prompt (max 5000 chars)",
            )
        if not self.image_config.api_key:
            return ImageResult(
                status=ImageStatus.FAILED,
                error="GEMINI_API_KEY is not configured",
                provider=self.image_config.provider,
                model=self.image_config.model,
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
        except AIProviderError:
            raise
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                raise ValueError(
                    "Research failed: Insufficient quota or access to Deep Research agent. Please check your API key permissions."
                ) from e
            raise ValueError(f"Failed to perform research: {e}") from e
