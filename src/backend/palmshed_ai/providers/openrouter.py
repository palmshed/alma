# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

"""
OpenRouter AI provider.

Talks to the OpenRouter ``/chat/completions`` endpoint (OpenAI-compatible
``messages`` format) over REST, with SSE streaming support.  Configurable
via ``OPENROUTER_API_KEY`` and ``OPENROUTER_BASE_URL`` (the base URL
override keeps the provider testable without network access).

Mock keys produce deterministic synthetic responses identical to the
Gemini provider's.  Real-key failures are raised as classified
:class:`~palmshed_ai.providers.base.AIProviderError` exceptions.
"""

import logging
import os
from typing import Any, Dict, Iterator, List, Optional

import requests

from .. import models
from .base import (
    AIProvider,
    AIProviderError,
    CAPABILITY_CHAT,
    CAPABILITY_THINKING,
    CAPABILITY_WEB,
    classify_http_status,
    classify_network_error,
    last_user_query,
    normalize_messages,
)
from .gemini import SYNTHETIC_CHAT, SYNTHETIC_TEXT, SYNTHETIC_THINKING, is_mock_key

logger = logging.getLogger("palmshed_ai.providers.openrouter")

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(AIProvider):
    """OpenRouter provider using the OpenAI-compatible chat API."""

    name = "openrouter"
    display_name = "OpenRouter"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.base_url = (
            base_url or os.environ.get("OPENROUTER_BASE_URL") or DEFAULT_BASE_URL
        ).rstrip("/")
        self.session = requests.Session()
        self._last_model: Optional[str] = None

    @property
    def has_credentials(self) -> bool:
        return bool(self.api_key) and not is_mock_key(self.api_key)

    def model_for(self, capability: str) -> str:
        if capability == CAPABILITY_THINKING:
            return (
                os.environ.get("OPENROUTER_THINKING_MODEL")
                or models.OPENROUTER_THINKING_MODEL
            )
        if capability == CAPABILITY_WEB:
            return (
                os.environ.get("OPENROUTER_URL_CONTEXT_MODEL")
                or models.OPENROUTER_URL_CONTEXT_MODEL
            )
        return os.environ.get("OPENROUTER_MODEL") or models.OPENROUTER_MODEL

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        referer = os.environ.get("OPENROUTER_HTTP_REFERER")
        app_title = os.environ.get("OPENROUTER_APP_TITLE")
        if referer:
            headers["HTTP-Referer"] = referer
        if app_title:
            headers["X-Title"] = app_title
        return headers

    def _url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def _payload(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        stream: bool = False,
    ) -> Dict[str, Any]:
        return {
            "model": model,
            "messages": messages,
            "stream": stream,
        }

    def _normalize_messages(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        normalized = normalize_messages(messages)
        out: List[Dict[str, Any]] = []
        for msg in normalized:
            role = msg["role"]
            if role == "model":
                role = "assistant"
            out.append({"role": role, "content": msg["content"]})
        return out

    def _extract_text(self, data: Dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            raise AIProviderError(
                f"OpenRouter returned an empty response for model '{self._last_model}'",
                category="server",
                provider=self.display_name,
                model=self._last_model,
            )
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content
        parts = message.get("parts")
        if isinstance(parts, list):
            text_parts = [
                p.get("text", "")
                for p in parts
                if isinstance(p, dict) and p.get("type") == "text"
            ]
            joined = "".join(text_parts).strip()
            if joined:
                return joined
        raise AIProviderError(
            f"OpenRouter returned no text content for model '{self._last_model}'",
            category="server",
            provider=self.display_name,
            model=self._last_model,
        )

    def _extract_reasoning(self, data: Dict[str, Any]) -> List[str]:
        """Collect reasoning/thinking text from a completion response."""
        choices = data.get("choices") or []
        if not choices:
            return []
        message = choices[0].get("message") or {}
        raw = message.get("reasoning") or message.get("reasoning_details")
        if isinstance(raw, str):
            stripped = raw.strip()
            return [stripped] if stripped else []
        if isinstance(raw, list):
            out: List[str] = []
            for item in raw:
                if isinstance(item, str):
                    text = item.strip()
                elif isinstance(item, dict):
                    text = str(item.get("text") or item.get("content") or "").strip()
                else:
                    continue
                if text:
                    out.append(text)
            return out
        return []

    def _post(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        stream: bool = False,
    ) -> requests.Response:
        if not self.api_key:
            raise AIProviderError(
                "OPENROUTER_API_KEY is not configured",
                category="auth",
                http_status=401,
                provider=self.display_name,
                model=model,
            )
        try:
            response = self.session.post(
                self._url(),
                headers=self._headers(),
                json=self._payload(messages, model, stream=stream),
                timeout=(15, 120),
                stream=stream,
            )
        except requests.exceptions.RequestException as e:
            raise classify_network_error(e, self.display_name, model) from e
        return response

    def _complete(self, messages: List[Dict[str, Any]], model: str) -> Dict[str, Any]:
        self._last_model = model
        response = self._post(messages, model)
        if response.status_code >= 400:
            raise self._classify_response(response, model)
        try:
            data = response.json()
        except ValueError as e:
            raise AIProviderError(
                f"OpenRouter returned invalid JSON for model '{model}'",
                category="server",
                provider=self.display_name,
                model=model,
            ) from e
        actual = data.get("model")
        if actual:
            self._last_model = actual
        return data

    def _classify_response(
        self, response: requests.Response, model: str
    ) -> AIProviderError:
        detail = response.text[:300].strip() or f"HTTP {response.status_code}"
        return classify_http_status(
            response.status_code, self.display_name, model, detail
        )

    # ── Text generation ──────────────────────────────────────────────
    def generate_text(self, prompt: str, model: Optional[str] = None) -> str:
        """Generate a plain text response for ``prompt``."""
        if not prompt or len(prompt) > 5000:
            raise ValueError("Invalid prompt")
        if self.synthetic:
            return SYNTHETIC_TEXT.format(query=prompt[:60])
        messages = [{"role": "user", "content": prompt}]
        data = self._complete(messages, model or self.model_for(CAPABILITY_CHAT))
        return self._extract_text(data)

    def generate_chat(self, messages: List[dict], model: Optional[str] = None) -> str:
        """Generate a response from a conversation message list."""
        if not messages:
            raise ValueError("No messages provided")
        if self.synthetic:
            query = last_user_query(messages) or "query"
            return SYNTHETIC_CHAT.format(query=query[:60])
        data = self._complete(
            self._normalize_messages(messages),
            model or self.model_for(CAPABILITY_CHAT),
        )
        return self._extract_text(data)

    def generate_chat_with_thinking(
        self, messages: List[dict], model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a response plus a thinking summary from a conversation."""
        if not messages:
            raise ValueError("No messages provided")
        if self.synthetic:
            return dict(SYNTHETIC_THINKING)
        data = self._complete(
            self._normalize_messages(messages),
            model or self.model_for(CAPABILITY_THINKING),
        )
        response = self._extract_text(data)
        return {"response": response, "thinking_summary": self._extract_reasoning(data)}

    def generate_text_with_thinking(
        self, prompt: str, model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a response plus a thinking summary from a prompt."""
        if not prompt or len(prompt) > 5000:
            raise ValueError("Invalid prompt")
        if self.synthetic:
            return dict(SYNTHETIC_THINKING)
        messages = [{"role": "user", "content": prompt}]
        data = self._complete(messages, model or self.model_for(CAPABILITY_THINKING))
        response = self._extract_text(data)
        return {"response": response, "thinking_summary": self._extract_reasoning(data)}

    def generate_chat_with_url_context(
        self, messages: List[dict], model: Optional[str] = None
    ) -> str:
        """Generate a response from a conversation with URL context."""
        if not messages:
            raise ValueError("No messages provided")
        if self.synthetic:
            query = last_user_query(messages) or "query"
            return SYNTHETIC_CHAT.format(query=query[:60])
        data = self._complete(
            self._normalize_messages(messages),
            model or self.model_for(CAPABILITY_WEB),
        )
        return self._extract_text(data)

    def generate_text_with_url_context(
        self, prompt: str, model: Optional[str] = None
    ) -> str:
        """Generate a response from a prompt with URL context."""
        if not prompt or len(prompt) > 5000:
            raise ValueError("Invalid prompt")
        if self.synthetic:
            return SYNTHETIC_TEXT.format(query=prompt[:60])
        messages = [{"role": "user", "content": prompt}]
        data = self._complete(messages, model or self.model_for(CAPABILITY_WEB))
        return self._extract_text(data)

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
        resolved_model = model or self.model_for(CAPABILITY_CHAT)
        response = self._post(
            self._normalize_messages(messages), resolved_model, stream=True
        )
        if response.status_code >= 400:
            raise self._classify_response(response, resolved_model)
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[len("data:") :].strip()
            if not payload or payload == "[DONE]":
                break
            try:
                chunk = _json_loads(payload)
            except ValueError as e:
                raise AIProviderError(
                    f"OpenRouter returned invalid stream JSON: {payload[:120]}",
                    category="server",
                    provider=self.display_name,
                    model=resolved_model,
                ) from e
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            text = delta.get("content")
            if isinstance(text, str) and text:
                yield text


def _json_loads(payload: str) -> Dict[str, Any]:
    import json

    return json.loads(payload)
