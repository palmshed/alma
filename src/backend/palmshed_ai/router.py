# SPDX-FileCopyrightText: Copyright (c) 2026 Palmshed
# SPDX-License-Identifier: MIT

"""
AI router: the single entry point for all text generation.

Routes never talk to a concrete provider.  They call :class:`AIRouter`,
which applies a small deterministic policy:

1. capability → preferred model (per provider),
2. preferred provider (from ``AI_PROVIDER``, default ``auto``),
3. fallback to the next configured provider when the preferred one fails.

Provider failures are classified and re-raised as
:class:`~palmshed_ai.providers.base.AIProviderError`: never converted
into synthetic success.  When no provider has credentials the router uses
the synthetic provider so CI and verification still run, and reports it as
``synthetic/mock``.

Non-generation capabilities (TTS, image generation, deep research, Go text
processing) are delegated to the Gemini provider untouched.
"""

import logging
import os
from typing import Any, Dict, Iterator, List, Optional

from .providers.base import (
    AIProvider,
    AIProviderError,
    CAPABILITY_CHAT,
    CAPABILITY_THINKING,
    CAPABILITY_WEB,
    CATEGORY_UNKNOWN,
)
from .providers.registry import AIProviderRegistry

logger = logging.getLogger("palmshed_ai.router")


def _provider_order(config: str) -> List[str]:
    """Preference order of provider names for a router config value."""
    if config == "openrouter":
        return ["openrouter", "gemini"]
    return ["gemini", "openrouter"]


class AIRouter:
    """Routes generation requests to configured AI providers."""

    def __init__(self, provider: Optional[str] = None):
        self.config_provider = (
            (provider or os.environ.get("AI_PROVIDER", "auto")).strip().lower()
        )
        if self.config_provider not in ("auto", "gemini", "openrouter"):
            self.config_provider = "auto"
        self.providers: Dict[str, AIProvider] = {
            name: AIProviderRegistry.create(name) for name in ("gemini", "openrouter")
        }
        self.synthetic = AIProviderRegistry.create("synthetic")

    # ── Candidate selection ──────────────────────────────────────────

    def _candidates(self) -> List[AIProvider]:
        """Ordered providers that can serve requests, else synthetic."""
        ordered = [
            self.providers[name] for name in _provider_order(self.config_provider)
        ]
        available = [p for p in ordered if p.has_credentials]
        if available:
            return available
        return [self.synthetic]

    def _candidates_for(self, provider: Optional[str] = None) -> List[AIProvider]:
        """Ordered providers for a request, honoring a per-request preference.

        ``provider`` overrides the router's configured order for a single
        request (``gemini`` | ``openrouter`` | ``auto``).  The requested
        provider is tried first; the other configured providers remain as
        fallbacks.  Falls back to the synthetic provider when no credentials.
        """
        if not provider:
            return self._candidates()
        name = provider.strip().lower()
        if name not in ("gemini", "openrouter", "auto"):
            name = "auto"
        ordered = [self.providers[p] for p in _provider_order(name)]
        # Keep the requested provider at the front, dedupe, then append others.
        ordered = sorted(
            ordered,
            key=lambda p: 0 if p.name == name else 1,
        )
        available = [p for p in ordered if p.has_credentials]
        if available:
            return available
        return [self.synthetic]

    def status(self) -> Dict[str, Any]:
        """Describe the active routing configuration (for health/verify)."""
        available = self._candidates()
        if not available or available == [self.synthetic]:
            return {
                "config": self.config_provider,
                "provider": self.synthetic.describe(),
                "fallback": None,
                "available": [],
            }
        primary = available[0]
        return {
            "config": self.config_provider,
            "provider": primary.describe(),
            "fallback": available[1].describe() if len(available) > 1 else None,
            "available": [p.name for p in available],
        }

    def _info(self, provider: AIProvider, model: str, fallback: bool) -> Dict[str, Any]:
        return {
            "provider": provider.describe(),
            "provider_key": provider.name,
            "model": model,
            "fallback_used": fallback,
        }

    def _execute(
        self,
        capability: str,
        fn_name: str,
        args: tuple,
        kwargs: Dict[str, Any],
        info: Optional[Dict[str, Any]],
        provider: Optional[str] = None,
    ) -> Any:
        candidates = self._candidates_for(provider)
        last_error: Optional[AIProviderError] = None
        for index, provider in enumerate(candidates):
            model = provider.model_for(capability)
            try:
                result = getattr(provider, fn_name)(*args, model=model, **kwargs)
                if info is not None:
                    info.update(self._info(provider, model, index > 0))
                return result
            except AIProviderError as exc:
                last_error = exc
                logger.warning(
                    "[ai-router] %s failed (%s/%s): %s",
                    provider.name,
                    capability,
                    model,
                    exc,
                )
            except Exception as exc:
                last_error = AIProviderError(
                    str(exc),
                    category=CATEGORY_UNKNOWN,
                    provider=provider.name,
                    model=model,
                )
                logger.warning(
                    "[ai-router] %s raised %s for %s: %s",
                    provider.name,
                    exc.__class__.__name__,
                    capability,
                    exc,
                )
        if last_error is not None:
            raise last_error
        provider = self.synthetic
        model = provider.model_for(capability)
        result = getattr(provider, fn_name)(*args, model=model, **kwargs)
        if info is not None:
            info.update(self._info(provider, model, False))
        return result

    # ── Text generation entry points ─────────────────────────────────

    def generate_text(
        self,
        prompt: str,
        info: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
    ) -> str:
        return self._execute(
            CAPABILITY_CHAT, "generate_text", (prompt,), {}, info, provider
        )

    def generate_chat(
        self,
        messages: List[dict],
        info: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
    ) -> str:
        return self._execute(
            CAPABILITY_CHAT, "generate_chat", (messages,), {}, info, provider
        )

    def generate_chat_with_thinking(
        self,
        messages: List[dict],
        info: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._execute(
            CAPABILITY_THINKING,
            "generate_chat_with_thinking",
            (messages,),
            {},
            info,
            provider,
        )

    def generate_text_with_thinking(
        self,
        prompt: str,
        info: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._execute(
            CAPABILITY_THINKING,
            "generate_text_with_thinking",
            (prompt,),
            {},
            info,
            provider,
        )

    def generate_chat_with_url_context(
        self,
        messages: List[dict],
        info: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
    ) -> str:
        return self._execute(
            CAPABILITY_WEB,
            "generate_chat_with_url_context",
            (messages,),
            {},
            info,
            provider,
        )

    def generate_text_with_url_context(
        self,
        prompt: str,
        info: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
    ) -> str:
        return self._execute(
            CAPABILITY_WEB,
            "generate_text_with_url_context",
            (prompt,),
            {},
            info,
            provider,
        )

    def stream_chat(
        self,
        messages: List[dict],
        info: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
    ) -> Iterator[str]:
        candidates = self._candidates_for(provider)
        last_error: Optional[AIProviderError] = None
        for index, provider in enumerate(candidates):
            model = provider.model_for(CAPABILITY_CHAT)
            try:
                stream = provider.stream_chat(messages, model=model)
                first = next(stream)
                if info is not None:
                    info.update(self._info(provider, model, index > 0))
                return self._rest(first, stream)
            except StopIteration:
                continue
            except AIProviderError as exc:
                last_error = exc
                logger.warning(
                    "[ai-router] %s stream failed (%s): %s",
                    provider.name,
                    model,
                    exc,
                )
            except Exception as exc:
                last_error = AIProviderError(
                    str(exc),
                    category=CATEGORY_UNKNOWN,
                    provider=provider.name,
                    model=model,
                )
                logger.warning(
                    "[ai-router] %s stream raised %s: %s",
                    provider.name,
                    exc.__class__.__name__,
                    exc,
                )
        if last_error is not None:
            raise last_error
        provider = self.synthetic
        model = provider.model_for(CAPABILITY_CHAT)
        stream = provider.stream_chat(messages, model=model)
        first = next(stream)
        if info is not None:
            info.update(self._info(provider, model, False))
        return self._rest(first, stream)

    @staticmethod
    def _rest(first: str, stream: Iterator[str]) -> Iterator[str]:
        yield first
        for chunk in stream:
            yield chunk

    # ── Non-generation capabilities ──────────────────────────────────

    def text_to_speech(self, text: str) -> str:
        return self.providers["gemini"].text_to_speech(text)

    def process_text_go(self, text: str) -> str:
        return self.providers["gemini"].process_text_go(text)

    def generate_image(self, prompt: str) -> Any:
        return self.providers["gemini"].generate_image(prompt)

    def research_topic(self, topic: str) -> Dict[str, Any]:
        return self.providers["gemini"].research_topic(topic)


# Module-level singleton shared by the API layer and verification.
router = AIRouter()
