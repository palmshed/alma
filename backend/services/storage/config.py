import os
from dataclasses import dataclass


@dataclass
class StorageConfig:
    provider: str = "mock"
    bucket: str = "alma"
    base_path: str = ""
    public_url: str = ""
    max_upload_size_mb: int = 50

    @staticmethod
    def from_env() -> "StorageConfig":
        return StorageConfig(
            provider=os.getenv("STORAGE_PROVIDER", "mock").lower(),
            bucket=os.getenv("STORAGE_BUCKET", "alma"),
            base_path=os.getenv("STORAGE_BASE_PATH", ""),
            public_url=os.getenv("STORAGE_PUBLIC_URL", ""),
            max_upload_size_mb=int(os.getenv("MAX_UPLOAD_SIZE_MB", "50")),
        )

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    def is_valid(self) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if self.provider not in ("mock", "local", "cloud"):
            errors.append(f"Unknown storage provider: {self.provider}")
        if self.max_upload_size_mb < 1:
            errors.append("max_upload_size_mb must be >= 1")
        if self.provider == "local" and not self.base_path:
            errors.append("STORAGE_BASE_PATH is required for local provider")
        return (len(errors) == 0, errors)
