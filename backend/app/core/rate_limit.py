"""Per-user sliding-window rate limiter for LLM-backed endpoints.

In-memory by design: the app runs as a single instance on Render's free tier,
and the limit protects the Groq quota, not a distributed SLA. Swap for a
Redis-backed limiter if the app ever scales horizontally.
"""
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, status

from app.config import settings
from app.core.deps import get_current_user
from app.models.user import User

_hits: dict[str, deque[float]] = defaultdict(deque)


def _allow(key: str, limit: int, window_seconds: float) -> float | None:
    """Record a hit; return None if allowed, else seconds until the next slot."""
    now = time.monotonic()
    window = _hits[key]
    while window and now - window[0] > window_seconds:
        window.popleft()
    if len(window) >= limit:
        return window_seconds - (now - window[0])
    window.append(now)
    return None


async def rate_limit_queries(current_user: User = Depends(get_current_user)) -> User:
    retry_in = _allow(
        str(current_user.id),
        settings.QUERY_RATE_LIMIT,
        settings.QUERY_RATE_WINDOW_SECONDS,
    )
    if retry_in is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Query limit reached ({settings.QUERY_RATE_LIMIT} per "
                f"{int(settings.QUERY_RATE_WINDOW_SECONDS)}s). Try again shortly."
            ),
            headers={"Retry-After": str(max(1, int(retry_in)))},
        )
    return current_user
