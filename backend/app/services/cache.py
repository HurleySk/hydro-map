"""
Caching service for watershed delineation results.

Supports both file-based caching (default) and optional Redis caching.
"""

import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

from app.config import settings

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover - Redis optional dependency
    redis = None


class BaseCacheBackend:
    async def get(self, cache_key: str) -> Optional[Dict]:
        raise NotImplementedError

    async def set(self, cache_key: str, value: Dict) -> None:
        raise NotImplementedError

    async def clear(self) -> int:
        raise NotImplementedError


class FileCacheBackend(BaseCacheBackend):
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def _cache_file_path(self, cache_key: str) -> Path:
        key_hash = _hash_key(cache_key)
        return self.base_dir / f"{key_hash}.json"

    async def get(self, cache_key: str) -> Optional[Dict]:
        cache_file = self._cache_file_path(cache_key)
        if not cache_file.exists():
            return None

        try:
            return await asyncio.to_thread(_read_json, cache_file)
        except Exception as exc:  # pragma: no cover - logging path
            print(f"Warning: Failed to read cache file {cache_file}: {exc}")
            return None

    async def set(self, cache_key: str, value: Dict) -> None:
        cache_file = self._cache_file_path(cache_key)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            await asyncio.to_thread(_write_json, cache_file, value)
        except Exception as exc:  # pragma: no cover - logging path
            print(f"Warning: Failed to write cache file {cache_file}: {exc}")

    async def clear(self) -> int:
        if not self.base_dir.exists():
            return 0

        def _clear(directory: Path) -> int:
            removed = 0
            for cache_file in directory.glob("*.json"):
                try:
                    cache_file.unlink()
                    removed += 1
                except Exception as exc:  # pragma: no cover - logging path
                    print(f"Warning: Failed to delete cache file {cache_file}: {exc}")
            return removed

        return await asyncio.to_thread(_clear, self.base_dir)


class RedisCacheBackend(BaseCacheBackend):
    """Optional Redis-backed cache implementation."""

    def __init__(self) -> None:
        if redis is None:
            raise RuntimeError("Redis backend requested but redis package is not installed.")

        self._client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
        )
        self._prefix = "watershed:"

    def _redis_key(self, cache_key: str) -> str:
        return f"{self._prefix}{_hash_key(cache_key)}"

    async def get(self, cache_key: str) -> Optional[Dict]:
        loop = asyncio.get_running_loop()
        redis_key = self._redis_key(cache_key)
        raw = await loop.run_in_executor(None, self._client.get, redis_key)
        if raw is None:
            return None

        try:
            return json.loads(raw)
        except json.JSONDecodeError:  # pragma: no cover - logging path
            print(f"Warning: Failed to decode Redis cache entry for {redis_key}")
            return None

    async def set(self, cache_key: str, value: Dict) -> None:
        loop = asyncio.get_running_loop()
        redis_key = self._redis_key(cache_key)
        payload = json.dumps(value)
        await loop.run_in_executor(None, self._client.set, redis_key, payload)

    async def clear(self) -> int:
        loop = asyncio.get_running_loop()

        def _clear_keys() -> int:
            removed = 0
            for key in self._client.scan_iter(match=f"{self._prefix}*"):
                self._client.delete(key)
                removed += 1
            return removed

        return await loop.run_in_executor(None, _clear_keys)


_CACHE_BACKEND: Optional[BaseCacheBackend] = None


def _hash_key(cache_key: str) -> str:
    return hashlib.md5(cache_key.encode()).hexdigest()


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r") as handle:
        return json.load(handle)


def _write_json(path: Path, data: Dict) -> None:
    with path.open("w") as handle:
        json.dump(data, handle)


def _get_backend() -> BaseCacheBackend:
    global _CACHE_BACKEND
    if _CACHE_BACKEND is not None:
        return _CACHE_BACKEND

    backend_name = os.getenv("CACHE_BACKEND", "file").lower()
    if backend_name == "redis":
        try:
            _CACHE_BACKEND = RedisCacheBackend()
            return _CACHE_BACKEND
        except Exception as exc:  # pragma: no cover - logging path
            print(f"Warning: Falling back to file cache backend ({exc})")

    cache_dir = Path(settings.CACHE_DIR) / "watersheds"
    _CACHE_BACKEND = FileCacheBackend(cache_dir)
    return _CACHE_BACKEND


async def get_cached_watershed(cache_key: str) -> Optional[Dict]:
    """
    Retrieve cached watershed result.

    Args:
        cache_key: Unique key for the watershed (e.g., "lat,lon")

    Returns:
        Cached result dictionary or None if not found
    """
    if not settings.CACHE_ENABLED:
        return None

    backend = _get_backend()
    return await backend.get(cache_key)


async def cache_watershed(cache_key: str, result: Dict) -> None:
    """
    Cache watershed delineation result.

    Args:
        cache_key: Unique key for the watershed
        result: Result dictionary to cache
    """
    if not settings.CACHE_ENABLED:
        return

    backend = _get_backend()
    await backend.set(cache_key, result)


async def clear_cache() -> int:
    """
    Clear all cached watersheds.

    Returns:
        Number of cache entries deleted
    """
    if not settings.CACHE_ENABLED:
        return 0

    backend = _get_backend()
    return await backend.clear()
