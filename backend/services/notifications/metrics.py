# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
from dataclasses import dataclass, field


@dataclass
class NotificationMetrics:
    sent: int = 0
    failed: int = 0
    bounced: int = 0
    _durations: list[float] = field(default_factory=list, repr=False)

    @property
    def avg_duration_ms(self) -> float:
        if not self._durations:
            return 0.0
        return (sum(self._durations) / len(self._durations)) * 1000

    def record_sent(self) -> None:
        self.sent += 1

    def record_failed(self) -> None:
        self.failed += 1

    def record_bounced(self) -> None:
        self.bounced += 1

    def record_duration(self, seconds: float) -> None:
        self._durations.append(seconds)

    def snapshot(self) -> dict:
        return {
            "sent": self.sent,
            "failed": self.failed,
            "bounced": self.bounced,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
        }
