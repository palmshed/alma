# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
from dataclasses import dataclass, field


@dataclass
class StorageMetrics:
    uploads: int = 0
    downloads: int = 0
    deletes: int = 0
    lists: int = 0
    failures: int = 0
    _durations: list[float] = field(default_factory=list, repr=False)

    @property
    def avg_duration_ms(self) -> float:
        if not self._durations:
            return 0.0
        return (sum(self._durations) / len(self._durations)) * 1000

    def record_upload(self) -> None:
        self.uploads += 1

    def record_download(self) -> None:
        self.downloads += 1

    def record_delete(self) -> None:
        self.deletes += 1

    def record_list(self) -> None:
        self.lists += 1

    def record_failure(self) -> None:
        self.failures += 1

    def record_duration(self, seconds: float) -> None:
        self._durations.append(seconds)

    def snapshot(self) -> dict:
        return {
            "uploads": self.uploads,
            "downloads": self.downloads,
            "deletes": self.deletes,
            "lists": self.lists,
            "failures": self.failures,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
        }
