from typing import Any, Optional, Dict, Tuple
from datetime import datetime, timedelta
import hashlib
import json
from sqlalchemy.orm import Query
from ..config.database import DatabaseManager


class CacheManager:
    """Manages caching for repository queries with configurable invalidation policies."""

    _instance: Optional["CacheManager"] = None
    _cache: Dict[str, Tuple[Any, datetime]] = {}
    _hit_counts: Dict[str, int] = {}
    _default_ttl = timedelta(minutes=30)
    _max_cache_size = 1000  # Maximum number of cached items

    def __init__(self):
        if CacheManager._instance is not None:
            raise RuntimeError("Use CacheManager.get_instance()")

    @classmethod
    def get_instance(cls) -> "CacheManager":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def generate_cache_key(
        self, query: Query, params: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a unique cache key for a query."""
        # Get the SQL string
        sql = str(
            query.statement.compile(
                dialect=DatabaseManager.get_instance().get_engine().dialect,
                compile_kwargs={"literal_binds": True},
            )
        )

        # Combine SQL and parameters
        key_data = {"sql": sql, "params": params or {}}

        # Generate hash
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache if it exists and is not expired."""
        if key not in self._cache:
            return None

        value, expiry = self._cache[key]
        if datetime.now() > expiry:
            # Remove expired entry
            del self._cache[key]
            return None

        # Update hit count
        self._hit_counts[key] = self._hit_counts.get(key, 0) + 1
        return value

    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """Set a value in cache with expiration."""
        if ttl is None:
            ttl = self._default_ttl

        # Check cache size limit
        if len(self._cache) >= self._max_cache_size:
            self._evict_entries()

        expiry = datetime.now() + ttl
        self._cache[key] = (value, expiry)
        self._hit_counts[key] = 0

    def invalidate(self, key: str) -> None:
        """Invalidate a specific cache entry."""
        if key in self._cache:
            del self._cache[key]
            if key in self._hit_counts:
                del self._hit_counts[key]

    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate all cache entries matching a pattern."""
        keys_to_remove = [key for key in self._cache.keys() if pattern in key]
        for key in keys_to_remove:
            self.invalidate(key)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._hit_counts.clear()

    def get_hit_rate(self, key: str) -> float:
        """Get the hit rate for a specific cache key."""
        return self._hit_counts.get(key, 0)

    def _evict_entries(self) -> None:
        """Evict cache entries based on LRU and hit rate."""
        if not self._cache:
            return

        # Remove expired entries first
        now = datetime.now()
        expired = [key for key, (_, expiry) in self._cache.items() if now > expiry]
        for key in expired:
            self.invalidate(key)

        # If still over limit, remove least frequently used entries
        if len(self._cache) >= self._max_cache_size:
            entries = sorted(self._hit_counts.items(), key=lambda x: x[1])
            # Remove bottom 10% of entries
            num_to_remove = max(
                len(self._cache) - self._max_cache_size, len(self._cache) // 10
            )
            for key, _ in entries[:num_to_remove]:
                self.invalidate(key)


def cache_query(ttl: Optional[timedelta] = None):
    """Decorator for caching query results."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get cache manager
            cache_mgr = CacheManager.get_instance()

            # Generate cache key from function name, args, and kwargs
            key_data = {"func": func.__name__, "args": str(args), "kwargs": str(kwargs)}
            cache_key = hashlib.sha256(
                json.dumps(key_data, sort_keys=True).encode()
            ).hexdigest()

            # Check cache
            cached_result = cache_mgr.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute query and cache result
            result = await func(*args, **kwargs)
            cache_mgr.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator
