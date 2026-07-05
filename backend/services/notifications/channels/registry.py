from typing import Optional

from .base import NotificationChannel


class ChannelRegistry:
    _channels: dict[str, type[NotificationChannel]] = {}

    @classmethod
    def register(cls, name: str, channel_cls: type[NotificationChannel]) -> None:
        cls._channels[name] = channel_cls

    @classmethod
    def create(cls, name: str, **kwargs) -> NotificationChannel:
        channel_cls = cls._channels.get(name)
        if not channel_cls:
            registered = ", ".join(cls.available())
            raise ValueError(
                f"Unknown notification channel '{name}'. Registered: {registered}"
            )
        return channel_cls(**kwargs)

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._channels.keys())

    @classmethod
    def get(cls, name: str) -> Optional[type[NotificationChannel]]:
        return cls._channels.get(name)
