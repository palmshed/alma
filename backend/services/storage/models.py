from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class StorageStatus(Enum):
    UPLOADED = "uploaded"
    DOWNLOADED = "downloaded"
    DELETED = "deleted"
    EXISTS = "exists"
    NOT_FOUND = "not_found"
    FAILED = "failed"


@dataclass
class StorageObject:
    id: str
    name: str
    size: int = 0
    content_type: str = "application/octet-stream"
    etag: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)
    public_url: Optional[str] = None


@dataclass
class StorageResult:
    status: StorageStatus
    object: Optional[StorageObject] = None
    data: Optional[bytes] = None
    error: Optional[str] = None
    provider: str = ""
    duration_ms: float = 0.0


@dataclass
class StorageHealth:
    provider: str
    config_valid: bool
    config_errors: list[str] = field(default_factory=list)
    bucket: str = ""
    healthy: bool = True
