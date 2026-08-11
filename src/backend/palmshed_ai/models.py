# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

"""
Model configuration for the AI providers.
Centralized location for all model names used in the application.

Each provider resolves its models from environment variables with sensible
defaults.  ``AI_PROVIDER`` (``auto`` | ``gemini`` | ``openrouter``) selects
provider preference; per-provider keys and model overrides configure the
rest (see the application README / deployment docs).
"""

import os

# ── Gemini (direct) models ────────────────────────────────────────────
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_THINKING_MODEL = os.environ.get("GEMINI_THINKING_MODEL", "gemini-2.5-pro")
GEMINI_URL_CONTEXT_MODEL = os.environ.get(
    "GEMINI_URL_CONTEXT_MODEL", "gemini-3.5-flash"
)

# ── OpenRouter models ─────────────────────────────────────────────────
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/auto")
OPENROUTER_THINKING_MODEL = os.environ.get(
    "OPENROUTER_THINKING_MODEL", "openrouter/auto"
)
OPENROUTER_URL_CONTEXT_MODEL = os.environ.get(
    "OPENROUTER_URL_CONTEXT_MODEL", "openrouter/auto"
)

# ── Legacy aliases (Gemini defaults) ──────────────────────────────────
TEXT_MODEL = GEMINI_MODEL
THINKING_MODEL = GEMINI_THINKING_MODEL
URL_CONTEXT_MODEL = GEMINI_URL_CONTEXT_MODEL

# ── Image generation provider and model ───────────────────────────────
IMAGE_PROVIDER = "gemini"
IMAGE_MODEL = "gemini-2.5-flash-image"

# ── Deep Research agent ───────────────────────────────────────────────
DEEP_RESEARCH_MODEL = "deep-research-pro-preview-12-2025"
