# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

"""
Image generation providers for Alma.
Supports multiple AI providers (Gemini, Imagen) through a unified interface.
"""

import os
import uuid
import tempfile
import mimetypes
from google import genai as google_genai
from google.genai import types

# Vertex AI for Imagen models
try:
    import vertexai
    from vertexai.preview.vision_models import ImageGenerationModel

    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False


class ImageProvider:
    """Base class for image generation providers."""

    def generate_image(self, prompt: str, model: str) -> str:
        """Generate image and return file path."""
        raise NotImplementedError


class GeminiImageProvider(ImageProvider):
    """Image generation using Gemini API."""

    def __init__(self, api_key: str):
        self.client = google_genai.Client(api_key=api_key)

    def generate_image(self, prompt: str, model: str) -> str:
        """Generate image using Gemini API."""
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=f"Generate an image of: {prompt}"),
                ],
            ),
        ]
        generate_content_config = types.GenerateContentConfig(
            response_modalities=["image", "text"],
            response_mime_type="text/plain",
        )
        response = self.client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        if (
            response.candidates
            and response.candidates[0].content
            and response.candidates[0].content.parts
        ):
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    file_extension = mimetypes.guess_extension(
                        part.inline_data.mime_type
                    )
                    filename = f"{uuid.uuid4()}{file_extension}"
                    filepath = os.path.join(
                        tempfile.gettempdir(), "generated_images", filename
                    )
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    with open(filepath, "wb") as f:
                        f.write(part.inline_data.data)
                    return filepath
        raise ValueError("Failed to generate image")


class ImagenImageProvider(ImageProvider):
    """Image generation using Imagen via Vertex AI."""

    def __init__(self):
        """Initialize Vertex AI once for better performance."""
        if VERTEX_AI_AVAILABLE:
            # Get Vertex AI credentials from environment
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
            location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

            if not project_id:
                raise ValueError(
                    "GOOGLE_CLOUD_PROJECT environment variable required for Imagen models"
                )

            # Initialize Vertex AI once
            vertexai.init(project=project_id, location=location)

        # Cache for model instances
        self._model_cache = {}

    def generate_image(self, prompt: str, model: str) -> str:
        """Generate image using Imagen via Vertex AI."""
        if not VERTEX_AI_AVAILABLE:
            raise ValueError(
                "Vertex AI not available. Install google-cloud-aiplatform package."
            )

        # Get cached model or create new one
        if model not in self._model_cache:
            self._model_cache[model] = ImageGenerationModel.from_pretrained(model)

        imagen_model = self._model_cache[model]

        # Generate image
        images = imagen_model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="1:1",
            safety_filter_level="block_some",
            person_generation="allow_adult",
        )

        if images and len(images) > 0:
            filename = f"{uuid.uuid4()}.png"
            filepath = os.path.join(tempfile.gettempdir(), "generated_images", filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # Save the image
            images[0].save(location=filepath, include_generation_parameters=False)
            return filepath

        raise ValueError("Failed to generate image with Imagen")


class ImageGenerationService:
    """Unified service for image generation across multiple providers."""

    def __init__(self, api_key: str):
        self.providers = {
            "gemini": GeminiImageProvider(api_key),
            "imagen": ImagenImageProvider(),
        }

    def generate_image(self, prompt: str, model: str) -> str:
        """Generate image using the appropriate provider based on model name."""
        # Centralize prompt validation to follow DRY principle
        if not prompt or len(prompt) > 5000:
            raise ValueError("Invalid prompt")

        if model.startswith("imagen-"):
            provider = self.providers.get("imagen")
            if not provider:
                raise ValueError("Imagen provider not available")
            return provider.generate_image(prompt, model)
        else:
            # Default to Gemini for other models
            provider = self.providers.get("gemini")
            if not provider:
                raise ValueError("Gemini provider not available")
            return provider.generate_image(prompt, model)
