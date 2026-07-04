import os
import uuid
import tempfile
import mimetypes
from abc import ABC, abstractmethod
from typing import Optional

from google import genai as google_genai
from google.genai import types

from .image_models import ImageConfig, ImageResult, ImageStatus

try:
    import vertexai
    from vertexai.preview.vision_models import ImageGenerationModel

    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False


class ImageProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> ImageResult: ...

    @property
    @abstractmethod
    def provider_type(self) -> str: ...


class GeminiFlashImage(ImageProvider):
    def __init__(self, config: ImageConfig):
        self.client = google_genai.Client(api_key=config.api_key)
        self._model = config.model
        self._provider = config.provider

    @property
    def provider_type(self) -> str:
        return self._provider

    def generate(self, prompt: str) -> ImageResult:
        try:
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
                model=self._model,
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
                            tempfile.gettempdir(),
                            "generated_images",
                            filename,
                        )
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        with open(filepath, "wb") as f:
                            f.write(part.inline_data.data)
                        return ImageResult(
                            status=ImageStatus.OK,
                            filepath=filepath,
                            provider=self._provider,
                            model=self._model,
                            mime_type=part.inline_data.mime_type,
                            size_bytes=len(part.inline_data.data),
                        )
            return ImageResult(
                status=ImageStatus.FAILED,
                error="No image data in response",
                provider=self._provider,
                model=self._model,
            )
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                return ImageResult(
                    status=ImageStatus.QUOTA_EXCEEDED,
                    error="Daily image generation quota exhausted",
                    provider=self._provider,
                    model=self._model,
                )
            if "503" in msg or "UNAVAILABLE" in msg:
                return ImageResult(
                    status=ImageStatus.UNAVAILABLE,
                    error="Image generation temporarily unavailable",
                    provider=self._provider,
                    model=self._model,
                )
            if "only supports text output" in msg:
                return ImageResult(
                    status=ImageStatus.UNSUPPORTED,
                    error=f"Model {self._model} does not support image generation",
                    provider=self._provider,
                    model=self._model,
                )
            return ImageResult(
                status=ImageStatus.FAILED,
                error=msg,
                provider=self._provider,
                model=self._model,
            )


class VertexImagen(ImageProvider):
    def __init__(self, config: ImageConfig):
        self._model = config.model
        self._provider = config.provider
        self._model_cache = {}

        if VERTEX_AI_AVAILABLE:
            project_id = config.project_id
            if not project_id:
                raise ValueError(
                    "GOOGLE_CLOUD_PROJECT required for Vertex AI image generation"
                )
            vertexai.init(project=project_id, location=config.location)

    @property
    def provider_type(self) -> str:
        return self._provider

    def generate(self, prompt: str) -> ImageResult:
        if not VERTEX_AI_AVAILABLE:
            return ImageResult(
                status=ImageStatus.UNSUPPORTED,
                error="Vertex AI not available. Install google-cloud-aiplatform",
                provider=self._provider,
                model=self._model,
            )

        try:
            if self._model not in self._model_cache:
                self._model_cache[self._model] = ImageGenerationModel.from_pretrained(
                    self._model
                )

            imagen_model = self._model_cache[self._model]
            images = imagen_model.generate_images(
                prompt=prompt,
                number_of_images=1,
                aspect_ratio="1:1",
                safety_filter_level="block_some",
                person_generation="allow_adult",
            )

            if images and len(images) > 0:
                filename = f"{uuid.uuid4()}.png"
                filepath = os.path.join(
                    tempfile.gettempdir(), "generated_images", filename
                )
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                images[0].save(location=filepath, include_generation_parameters=False)
                return ImageResult(
                    status=ImageStatus.OK,
                    filepath=filepath,
                    provider=self._provider,
                    model=self._model,
                    mime_type="image/png",
                    size_bytes=os.path.getsize(filepath),
                )

            return ImageResult(
                status=ImageStatus.FAILED,
                error="No image generated",
                provider=self._provider,
                model=self._model,
            )

        except Exception as e:
            msg = str(e)
            if "429" in msg or "quota" in msg.lower():
                return ImageResult(
                    status=ImageStatus.QUOTA_EXCEEDED,
                    error="Vertex AI image generation quota exceeded",
                    provider=self._provider,
                    model=self._model,
                )
            return ImageResult(
                status=ImageStatus.FAILED,
                error=msg,
                provider=self._provider,
                model=self._model,
            )


class MockImage(ImageProvider):
    @property
    def provider_type(self) -> str:
        return "mock"

    def generate(self, prompt: str) -> ImageResult:
        import struct
        import zlib

        width, height = 64, 64
        raw_data = b""
        for y in range(height):
            raw_data += b"\x00"
            for x in range(width):
                raw_data += b"\xff\x00\x00"
        compressor = zlib.compressobj()
        compressed = compressor.compress(raw_data) + compressor.flush()

        def chunk(chunk_type, data):
            c = chunk_type + data
            return (
                struct.pack(">I", len(data))
                + c
                + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
            )

        ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        idat = chunk(b"IDAT", compressed)
        iend = chunk(b"IEND", b"")

        png_data = b"\x89PNG\r\n\x1a\n" + ihdr + idat + iend

        filename = f"{uuid.uuid4()}.png"
        filepath = os.path.join(tempfile.gettempdir(), "generated_images", filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(png_data)

        return ImageResult(
            status=ImageStatus.OK,
            filepath=filepath,
            provider="mock",
            model="mock",
            mime_type="image/png",
            width=width,
            height=height,
            size_bytes=len(png_data),
        )


class ImageProviderRegistry:
    _providers: dict[str, type[ImageProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_cls: type[ImageProvider]) -> None:
        cls._providers[name] = provider_cls

    @classmethod
    def create(cls, name: str, config: ImageConfig) -> ImageProvider:
        provider_cls = cls._providers.get(name)
        if not provider_cls:
            registered = ", ".join(cls.available())
            raise ValueError(
                f"Unknown image provider '{name}'. Registered: {registered}"
            )
        return provider_cls(config)

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._providers.keys())

    @classmethod
    def get(cls, name: str) -> Optional[type[ImageProvider]]:
        return cls._providers.get(name)


ImageProviderRegistry.register("gemini", GeminiFlashImage)
ImageProviderRegistry.register("vertex", VertexImagen)
ImageProviderRegistry.register("mock", MockImage)
