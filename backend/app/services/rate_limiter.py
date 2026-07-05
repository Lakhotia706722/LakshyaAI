"""
Rate limiter using Redis with in-memory fallback.

Used for:
- Auth endpoint limiting (per IP)
- Per-org API limiting
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import HTTPException

from app.config import get_settings

settings = get_settings()

# ─────────────────────────────────────────────────────────────
# In-memory fallback (single process only, resets on restart)
# ─────────────────────────────────────────────────────────────

_memory_store: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))


def _memory_check(key: str, max_attempts: int, window_seconds: int) -> None:
    count, window_start = _memory_store[key]
    now = time.time()
    if now - window_start > window_seconds:
        # New window
        _memory_store[key] = (1, now)
        return
    if count >= max_attempts:
        retry_after = int(window_seconds - (now - window_start))
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    _memory_store[key] = (count + 1, window_start)


# ─────────────────────────────────────────────────────────────
# Redis-backed check (preferred in production)
# ─────────────────────────────────────────────────────────────

_redis_client = None
_redis_warned = False


def _get_redis():
    global _redis_client, _redis_warned
    if _redis_client is not None:
        return _redis_client
    if not settings.REDIS_URL:
        return None
    try:
        import redis
        client = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        client.ping()
        _redis_client = client
        return client
    except Exception as e:
        if not _redis_warned:
            import logging
            logging.getLogger(__name__).warning(
                f"Redis unavailable ({e}); rate limiting falling back to in-memory store. "
                "This is NOT safe for multi-instance deployments."
            )
            _redis_warned = True
        return None


def _redis_check(r, key: str, max_attempts: int, window_seconds: int) -> None:
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.ttl(key)
    count, ttl = pipe.execute()
    if count == 1:
        r.expire(key, window_seconds)
        ttl = window_seconds
    if count > max_attempts:
        retry_after = ttl if ttl > 0 else window_seconds
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

async def check_rate_limit(key: str, max_attempts: int, window_seconds: int) -> None:
    """
    Check and increment a rate limit counter.
    Raises HTTP 429 with Retry-After header if limit exceeded.

    key            — unique string per subject (e.g. "login:1.2.3.4")
    max_attempts   — max allowed within the window
    window_seconds — sliding window size in seconds
    """
    r = _get_redis()
    if r:
        _redis_check(r, key, max_attempts, window_seconds)
    else:
        _memory_check(key, max_attempts, window_seconds)
