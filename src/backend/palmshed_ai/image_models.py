# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
import os
from dataclasses import dataclass
from enum import Enum


class ImageProviderType(Enum):
    GEMINI = "gemini"
    VERTEX = "vertex"
    MOCK = "mock"


class ImageStatus(Enum):
    OK = "ok"
    FAILED = "failed"
    QUOTA_EXCEEDED = "quota_exceeded"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"


@dataclass
class ImageConfig:
    provider: str = "gemini"
    model: str = "gemini-2.5-flash-image"
    api_key: str = ""
    project_id: str = ""
    location: str = "us-central1"

    @classmethod
    def from_env(cls) -> "ImageConfig":
        return cls(
            provider=os.environ.get("IMAGE_PROVIDER", "gemini"),
            model=os.environ.get("IMAGE_MODEL", "gemini-2.5-flash-image"),
            api_key=os.environ.get("GEMINI_API_KEY", ""),
            project_id=os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )


@dataclass
class ImageResult:
    status: ImageStatus = ImageStatus.FAILED
    filepath: str = ""
    error: str = ""
    provider: str = ""
    model: str = ""
    mime_type: str = ""
    width: int = 0
    height: int = 0
    size_bytes: int = 0
