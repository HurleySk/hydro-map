"""
Caching service for watershed delineation results.

Supports both file-based caching (default) and Redis caching.
"""

import json
from pathlib import Path
from typing import Optional, Dict
import hashlib

from app.config import settings


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

    # File-based cache
    cache_file = _get_cache_file_path(cache_key)
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to read cache file {cache_file}: {e}")
            return None

    return None


async def cache_watershed(cache_key: str, result: Dict) -> None:
    """
    Cache watershed delineation result.

    Args:
        cache_key: Unique key for the watershed
        result: Result dictionary to cache
    """
    if not settings.CACHE_ENABLED:
        return

    # File-based cache
    cache_file = _get_cache_file_path(cache_key)
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(cache_file, 'w') as f:
            json.dump(result, f)
    except Exception as e:
        print(f"Warning: Failed to write cache file {cache_file}: {e}")


def _get_cache_file_path(cache_key: str) -> Path:
    """
    Generate cache file path for a given key.

    Args:
        cache_key: Cache key string

    Returns:
        Path to cache file
    """
    # Hash the key to create a valid filename
    key_hash = hashlib.md5(cache_key.encode()).hexdigest()
    return Path(settings.CACHE_DIR) / "watersheds" / f"{key_hash}.json"


async def clear_cache() -> int:
    """
    Clear all cached watersheds.

    Returns:
        Number of cache files deleted
    """
    cache_dir = Path(settings.CACHE_DIR) / "watersheds"
    if not cache_dir.exists():
        return 0

    count = 0
    for cache_file in cache_dir.glob("*.json"):
        try:
            cache_file.unlink()
            count += 1
        except Exception as e:
            print(f"Warning: Failed to delete cache file {cache_file}: {e}")

    return count
