# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
from dataclasses import dataclass, field


@dataclass
class AuthMetrics:
    registrations: int = 0
    logins: int = 0
    verifications: int = 0
    refreshes: int = 0
    failures: int = 0
    _durations: list[float] = field(default_factory=list, repr=False)

    @property
    def avg_duration_ms(self) -> float:
        if not self._durations:
            return 0.0
        return (sum(self._durations) / len(self._durations)) * 1000

    def record_registration(self) -> None:
        self.registrations += 1

    def record_login(self) -> None:
        self.logins += 1

    def record_verification(self) -> None:
        self.verifications += 1

    def record_refresh(self) -> None:
        self.refreshes += 1

    def record_failure(self) -> None:
        self.failures += 1

    def record_duration(self, seconds: float) -> None:
        self._durations.append(seconds)

    def snapshot(self) -> dict:
        return {
            "registrations": self.registrations,
            "logins": self.logins,
            "verifications": self.verifications,
            "refreshes": self.refreshes,
            "failures": self.failures,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
        }
