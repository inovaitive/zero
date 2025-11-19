"""
Response Caching for ZERO Assistant.

This module provides intelligent caching of full responses to reduce latency
for common or repeated queries.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class CachedResponse:
    """Cached response data."""

    user_input: str
    intent: str
    response_text: str
    timestamp: float
    hit_count: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def is_expired(self, ttl: float) -> bool:
        """
        Check if cache entry is expired.

        Args:
            ttl: Time-to-live in seconds

        Returns:
            True if expired
        """
        if ttl <= 0:
            return False  # No expiration
        return (time.time() - self.timestamp) > ttl

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CachedResponse':
        """Create from dictionary."""
        return cls(**data)


class ResponseCache:
    """
    Intelligent response caching system.

    Features:
    - Semantic caching (similar queries map to same response)
    - TTL-based expiration
    - Hit count tracking
    - Persistent cache storage
    - Cache warming for common queries
    """

    # Queries that should always be cached with long TTL
    ALWAYS_CACHE = [
        "hello",
        "hi",
        "hey",
        "thank you",
        "thanks",
        "goodbye",
        "bye",
        "what can you do",
        "help",
        "who are you",
        "what's your name",
    ]

    # Intents that should NOT be cached (dynamic responses)
    NO_CACHE_INTENTS = [
        "timer.status",
        "timer.list",
        "app.list",
        "system.status",
        "weather.query",  # Weather changes frequently
    ]

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl: float = 3600,  # 1 hour default
        max_entries: int = 1000,
        enabled: bool = True
    ):
        """
        Initialize response cache.

        Args:
            cache_dir: Directory for cache storage
            ttl: Time-to-live for cache entries (seconds)
            max_entries: Maximum number of cached responses
            enabled: Whether caching is enabled
        """
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent.parent / "data" / "cache" / "responses"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.ttl = ttl
        self.max_entries = max_entries
        self.enabled = enabled

        self._cache: Dict[str, CachedResponse] = {}
        self._load_cache()

        # Statistics
        self.hits = 0
        self.misses = 0

        logger.info(f"Response cache initialized (dir={cache_dir}, ttl={ttl}s, enabled={enabled})")

    def get(self, user_input: str, intent: Optional[str] = None) -> Optional[CachedResponse]:
        """
        Get cached response for user input.

        Args:
            user_input: User's input text
            intent: Optional intent to check against no-cache list

        Returns:
            Cached response or None if not found/expired
        """
        if not self.enabled:
            return None

        # Check if intent should not be cached
        if intent and intent in self.NO_CACHE_INTENTS:
            return None

        # Generate cache key
        cache_key = self._generate_key(user_input)

        # Check cache
        if cache_key in self._cache:
            cached = self._cache[cache_key]

            # Check expiration
            if cached.is_expired(self.ttl):
                logger.debug(f"Cache expired for: '{user_input}'")
                del self._cache[cache_key]
                self.misses += 1
                return None

            # Cache hit
            cached.hit_count += 1
            self.hits += 1
            logger.info(f"🎯 Cache hit for: '{user_input}' (hits: {cached.hit_count})")
            return cached

        # Cache miss
        self.misses += 1
        return None

    def set(
        self,
        user_input: str,
        intent: str,
        response_text: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Cache a response.

        Args:
            user_input: User's input text
            intent: Classified intent
            response_text: Response to cache
            metadata: Optional metadata
        """
        if not self.enabled:
            return

        # Check if intent should not be cached
        if intent in self.NO_CACHE_INTENTS:
            logger.debug(f"Intent '{intent}' not cacheable, skipping")
            return

        # Check max entries
        if len(self._cache) >= self.max_entries:
            self._evict_oldest()

        # Generate cache key
        cache_key = self._generate_key(user_input)

        # Create cache entry
        cached = CachedResponse(
            user_input=user_input,
            intent=intent,
            response_text=response_text,
            timestamp=time.time(),
            metadata=metadata or {}
        )

        self._cache[cache_key] = cached
        logger.debug(f"Cached response for: '{user_input}'")

        # Persist cache
        self._save_cache()

    def _generate_key(self, text: str) -> str:
        """
        Generate cache key from text.

        Normalizes text for semantic caching.

        Args:
            text: Input text

        Returns:
            Cache key (hash)
        """
        # Normalize text
        normalized = text.lower().strip()

        # Remove common variations
        normalized = normalized.replace("?", "")
        normalized = normalized.replace("!", "")
        normalized = normalized.replace(".", "")

        # Generate hash
        return hashlib.md5(normalized.encode()).hexdigest()

    def _evict_oldest(self):
        """Evict oldest cache entry."""
        if not self._cache:
            return

        # Find oldest entry
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].timestamp
        )

        logger.debug(f"Evicting cache entry: '{self._cache[oldest_key].user_input}'")
        del self._cache[oldest_key]

    def _load_cache(self):
        """Load cache from disk."""
        cache_file = self.cache_dir / "response_cache.json"

        if not cache_file.exists():
            logger.debug("No cache file found, starting fresh")
            return

        try:
            with open(cache_file, "r") as f:
                data = json.load(f)

            # Load entries
            for key, entry_data in data.items():
                try:
                    entry = CachedResponse.from_dict(entry_data)

                    # Skip expired entries
                    if not entry.is_expired(self.ttl):
                        self._cache[key] = entry

                except Exception as e:
                    logger.warning(f"Failed to load cache entry: {e}")

            logger.info(f"Loaded {len(self._cache)} cached responses")

        except Exception as e:
            logger.error(f"Failed to load cache: {e}")

    def _save_cache(self):
        """Save cache to disk."""
        cache_file = self.cache_dir / "response_cache.json"

        try:
            # Convert to serializable format
            data = {
                key: entry.to_dict()
                for key, entry in self._cache.items()
            }

            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self._cache)} cached responses")

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Response cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0

        return {
            'enabled': self.enabled,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'total_entries': len(self._cache),
            'max_entries': self.max_entries,
            'ttl': self.ttl,
        }

    def get_top_cached(self, limit: int = 10) -> list:
        """
        Get most frequently cached responses.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of cached responses sorted by hit count
        """
        sorted_cache = sorted(
            self._cache.values(),
            key=lambda c: c.hit_count,
            reverse=True
        )
        return sorted_cache[:limit]


# Global cache instance
_response_cache = None


def get_response_cache(config: Optional[Dict[str, Any]] = None) -> ResponseCache:
    """
    Get the global response cache instance.

    Args:
        config: Optional configuration

    Returns:
        ResponseCache instance
    """
    global _response_cache

    if _response_cache is None:
        if config is None:
            config = {}

        cache_config = config.get('response_cache', {})

        _response_cache = ResponseCache(
            ttl=cache_config.get('ttl', 3600),
            max_entries=cache_config.get('max_entries', 1000),
            enabled=cache_config.get('enabled', True),
        )

    return _response_cache
