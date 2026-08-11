# SPDX-FileCopyrightText: Copyright (c) 2026 Palmshed
# SPDX-License-Identifier: MIT

"""
Synthetic AI provider.

Used by the router only when no real provider credentials are configured
(e.g. CI with ``GEMINI_API_KEY=dummy``).  Produces deterministic responses
so verification always runs, and is always reported as ``synthetic/mock``
in verification output so nobody mistakes it for a real model.
"""

from typing import Any, Dict, Iterator, List, Optional

from .base import (
    AIProvider,
    last_user_query,
)
from .gemini import SYNTHETIC_CHAT, SYNTHETIC_TEXT, SYNTHETIC_THINKING


class SyntheticProvider(AIProvider):
    """Deterministic mock provider for no-credential environments."""

    name = "synthetic"
    display_name = "Synthetic"

    @property
    def has_credentials(self) -> bool:
        return False

    def model_for(self, capability: str) -> str:
        return "synthetic"

    def generate_text(self, prompt: str, model: Optional[str] = None) -> str:
        if not prompt or len(prompt) > 5000:
            raise ValueError("Invalid prompt")
        return SYNTHETIC_TEXT.format(query=prompt[:60])

    def generate_chat(
        self, messages: List[Dict[str, Any]], model: Optional[str] = None
    ) -> str:
        if not messages:
            raise ValueError("No messages provided")
        query = last_user_query(messages) or "query"
        return SYNTHETIC_CHAT.format(query=query[:60])

    def generate_chat_with_thinking(
        self, messages: List[Dict[str, Any]], model: Optional[str] = None
    ) -> Dict[str, Any]:
        if not messages:
            raise ValueError("No messages provided")
        return dict(SYNTHETIC_THINKING)

    def generate_text_with_thinking(
        self, prompt: str, model: Optional[str] = None
    ) -> Dict[str, Any]:
        if not prompt or len(prompt) > 5000:
            raise ValueError("Invalid prompt")
        return dict(SYNTHETIC_THINKING)

    def generate_chat_with_url_context(
        self, messages: List[Dict[str, Any]], model: Optional[str] = None
    ) -> str:
        if not messages:
            raise ValueError("No messages provided")
        query = last_user_query(messages) or "query"
        return SYNTHETIC_CHAT.format(query=query[:60])

    def generate_text_with_url_context(
        self, prompt: str, model: Optional[str] = None
    ) -> str:
        if not prompt or len(prompt) > 5000:
            raise ValueError("Invalid prompt")
        return SYNTHETIC_TEXT.format(query=prompt[:60])

    def stream_chat(
        self, messages: List[Dict[str, Any]], model: Optional[str] = None
    ) -> Iterator[str]:
        if not messages:
            raise ValueError("No messages provided")
        query = last_user_query(messages) or "query"
        yield SYNTHETIC_CHAT.format(query=query[:60])
        return
