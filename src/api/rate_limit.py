"""Small in-memory sliding-window rate limiter for expensive endpoints.

Scope: only routes that can trigger upstream GitHub or AI provider work.
Health, docs, cached reads, and fixture serving are never limited.

Notes for production:
- Limits reset on restart and are per process. A multi-instance deployment
  needs Redis or another shared store.
- Client IP comes from the direct connection by default. Behind a proxy
  (e.g. Render), set TRUST_PROXY_HEADERS=1 to honor X-Forwarded-For. Do not
  enable that flag where headers are spoofable.
"""

import os
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException, Request

ASSESSMENT_LIMIT = 10
ASSESSMENT_WINDOW_SECONDS = 60
REVIEW_LIMIT = 5
REVIEW_WINDOW_SECONDS = 60


def trust_proxy_headers() -> bool:
    return os.environ.get("TRUST_PROXY_HEADERS", "") == "1"


def client_ip(request: Request) -> str:
    if trust_proxy_headers():
        forwarded = request.headers.get("x-forwarded-for", "")
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    if request.client is not None:
        return request.client.host
    return "unknown"


class RateLimiter:
    """Sliding-window limiter. Clock is injectable for deterministic tests."""

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock
        self.hits: dict[str, deque[float]] = {}

    def check(self, key: str) -> tuple[bool, float]:
        """Return (allowed, retry_after_seconds). Never raises."""
        now = self.clock()
        window_start = now - self.window_seconds
        bucket = self.hits.setdefault(key, deque())
        while bucket and bucket[0] <= window_start:
            bucket.popleft()
        if len(bucket) >= self.limit:
            retry_after = max(1.0, bucket[0] + self.window_seconds - now)
            return False, retry_after
        bucket.append(now)
        return True, 0.0

    def clear(self) -> None:
        self.hits.clear()


assessment_limiter = RateLimiter(ASSESSMENT_LIMIT, ASSESSMENT_WINDOW_SECONDS)
review_limiter = RateLimiter(REVIEW_LIMIT, REVIEW_WINDOW_SECONDS)


def reset_rate_limiters() -> None:
    assessment_limiter.clear()
    review_limiter.clear()


def check_or_429(request: Request, limiter: RateLimiter, scope: str) -> None:
    allowed, retry_after = limiter.check(client_ip(request))
    if allowed:
        return
    raise HTTPException(
        status_code=429,
        detail=f"rate limit exceeded for {scope}, retry later",
        headers={"Retry-After": str(int(retry_after))},
    )
