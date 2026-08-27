import re
import threading
import time
from collections import defaultdict, deque
from typing import Callable, Deque, Dict, Tuple

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.logger import logger


def parse_rate_limit(rate_str: str) -> Tuple[int, int]:
    """
    Parse rate limit strings such as '30/minute', '10/second', '100/hour'.
    Returns (max_requests, time_window_seconds).
    """
    pattern = r"^\s*(\d+)\s*/\s*(second|minute|hour|day)s?\s*$"
    match = re.match(pattern, rate_str.strip().lower())
    if not match:
        # Default fallback to 60 requests per minute
        return 60, 60

    count = int(match.group(1))
    unit = match.group(2)

    unit_multipliers = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
    }

    return count, unit_multipliers.get(unit, 60)


class InMemoryRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Key: (client_identifier, endpoint_key) -> deque of request timestamps
        self._history: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)

    def is_rate_limited(
        self,
        client_id: str,
        endpoint_key: str,
        max_requests: int,
        window_seconds: int,
    ) -> Tuple[bool, int]:
        """
        Check if request is rate limited.
        Returns (is_limited, retry_after_seconds).
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            history = self._history[(client_id, endpoint_key)]

            # Evict timestamps outside current sliding window
            while history and history[0] < window_start:
                history.popleft()

            if len(history) >= max_requests:
                # Calculate remaining seconds until oldest request expires
                oldest = history[0]
                retry_after = max(1, int(oldest + window_seconds - now))
                return True, retry_after

            # Record current timestamp
            history.append(now)
            return False, 0

    def reset(self):
        """Reset rate limiter state (useful for tests)."""
        with self._lock:
            self._history.clear()


limiter = InMemoryRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract real client IP considering forward headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


def rate_limit(rate_str_getter: Callable[[], str], endpoint_name: str):
    """
    FastAPI dependency generator for endpoint rate limiting.
    """

    async def dependency(request: Request):
        if not settings.RATE_LIMITING_ENABLED:
            return

        rate_str = rate_str_getter()
        max_requests, window_seconds = parse_rate_limit(rate_str)
        client_ip = get_client_ip(request)

        is_limited, retry_after = limiter.is_rate_limited(
            client_id=client_ip,
            endpoint_key=endpoint_name,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

        if is_limited:
            logger.warning(
                f"Rate limit exceeded for client {client_ip} on endpoint '{endpoint_name}' "
                f"({max_requests}/{window_seconds}s limit). Retry-After: {retry_after}s"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests allowed per window. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency


# Pre-built dependencies for key endpoints
rate_limit_chat = rate_limit(lambda: settings.RATE_LIMIT_CHAT, "chat")
rate_limit_upload = rate_limit(lambda: settings.RATE_LIMIT_UPLOAD, "upload")
rate_limit_delete = rate_limit(lambda: settings.RATE_LIMIT_DELETE, "delete")
