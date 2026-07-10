# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

"""
Model configuration for Gemini AI SDK.
Centralized location for all model names used in the application.
"""

# Text generation models
TEXT_MODEL = "gemini-2.5-flash"
THINKING_MODEL = "gemini-2.5-flash"
URL_CONTEXT_MODEL = "gemini-2.5-flash"

# Speech synthesis model
TTS_MODEL = "gemini-3.1-flash-tts-preview"

# Supported TTS voice names (passed to Gemini speech config)
TTS_VOICES = {
    "default": "Default voice",
    "Puck": "Puck (male)",
    "Charon": "Charon (female)",
    "Kore": "Kore (female)",
    "Fenrir": "Fenrir (male)",
}
DEFAULT_TTS_VOICE = "default"
DEFAULT_TTS_VOICE_NAME = "Puck"

# Image generation provider and model
IMAGE_PROVIDER = "gemini"
IMAGE_MODEL = "gemini-2.5-flash-image"

# Deep Research agent
DEEP_RESEARCH_MODEL = "deep-research-pro-preview-12-2025"
