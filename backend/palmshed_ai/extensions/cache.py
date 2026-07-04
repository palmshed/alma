# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

"""
Caching extension for Gemini AI SDK.
Provides simple in-memory caching and Redis support for API responses.
"""

import hashlib
import json
from typing import Any, Optional
import redis


class Cache:
    """Simple cache with in-memory and Redis support."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis = redis.from_url(redis_url) if redis_url else None
        self.memory_cache = {}

    def _key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function name and arguments."""
        key_data = json.dumps(
            {"func": func_name, "args": args, "kwargs": kwargs}, sort_keys=True
        )
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if self.redis:
            value = self.redis.get(key)
            return json.loads(value) if value else None
        return self.memory_cache.get(key)

    def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL."""
        if self.redis:
            self.redis.setex(key, ttl, json.dumps(value))
        else:
            self.memory_cache[key] = value

    def cached(self, ttl: int = 3600):
        """Decorator to cache function results."""

        def decorator(func):
            def wrapper(*args, **kwargs):
                key = self._key(func.__name__, args, kwargs)
                result = self.get(key)
                if result is not None:
                    return result
                result = func(*args, **kwargs)
                self.set(key, result, ttl)
                return result

            return wrapper

        return decorator


# Global cache instance
cache = Cache(redis_url=None)  # Set redis_url for Redis
