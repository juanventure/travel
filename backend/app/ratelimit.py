"""
Redis-backed per-IP rate limiting for public endpoints.

Uses a fixed 60-second window counter in Redis. Fails OPEN: if Redis is
unreachable we log and allow the request rather than locking everyone out.
Honours X-Forwarded-For so the real client IP is used behind a proxy/ALB.
"""
import os
import time

import redis.asyncio as aioredis
from fastapi import Request, HTTPException, status

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis = None


def _get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


def _client_ip(request: Request) -> str:
    # Behind a proxy/load balancer the first X-Forwarded-For entry is the client.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limiter(limit_per_minute: int, bucket: str):
    """FastAPI dependency factory enforcing `limit_per_minute` per IP for `bucket`."""

    async def _dependency(request: Request):
        try:
            r = _get_redis()
            ip = _client_ip(request)
            window = int(time.time() // 60)
            key = f"rl:{bucket}:{ip}:{window}"
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, 60)
            if count > limit_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please slow down and try again shortly.",
                )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 - fail open on Redis problems
            print(f"[ratelimit] check failed ({exc!r}); allowing request.")

    return _dependency
