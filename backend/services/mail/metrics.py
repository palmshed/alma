import time
from dataclasses import dataclass, field


@dataclass
class MailMetrics:
    queued: int = 0
    sent: int = 0
    failed: int = 0
    retried: int = 0
    _durations: list[float] = field(default_factory=list, repr=False)

    @property
    def avg_duration_ms(self) -> float:
        if not self._durations:
            return 0.0
        return (sum(self._durations) / len(self._durations)) * 1000

    @property
    def total_messages(self) -> int:
        return self.queued

    def record_queued(self) -> None:
        self.queued += 1

    def record_sent(self) -> None:
        self.sent += 1

    def record_failed(self) -> None:
        self.failed += 1

    def record_retried(self) -> None:
        self.retried += 1

    def record_duration(self, seconds: float) -> None:
        self._durations.append(seconds)

    def snapshot(self) -> dict:
        return {
            "queued": self.queued,
            "sent": self.sent,
            "failed": self.failed,
            "retried": self.retried,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
        }
