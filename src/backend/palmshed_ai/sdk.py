# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

"""
Backward-compatible facade for the Gemini provider.

The original ``GeminiAI`` class now lives in
``palmshed_ai.providers.gemini``.  This module re-exports it so existing
imports (``from palmshed_ai.sdk import GeminiAI``) keep working.  New code
should go through ``palmshed_ai.router`` instead.
"""

from .providers.gemini import GeminiAI, is_mock_key

__all__ = ["GeminiAI", "is_mock_key"]
