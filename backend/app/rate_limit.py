"""A small in-process rate limiter for the authentication endpoints.

ponytail: a dict and a deque, not Redis. This process is the only thing serving
the API, so a per-process counter is the whole truth; the moment there is a second
worker or a second container, each one enforces its own share of the limit and the
effective ceiling multiplies. Swap the store for Redis at that point — the call
sites do not change.
"""

import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

# Enough attempts for someone who genuinely forgot which password they used, far
# too few to search a password space.
LOGIN_MAX_ATTEMPTS = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "10"))
LOGIN_WINDOW_SECONDS = int(os.environ.get("LOGIN_WINDOW_SECONDS", "900"))  # 15 min

# Registration is a once-per-person action; a burst is either a script or a mistake.
REGISTER_MAX_ATTEMPTS = int(os.environ.get("REGISTER_MAX_ATTEMPTS", "5"))
REGISTER_WINDOW_SECONDS = int(os.environ.get("REGISTER_WINDOW_SECONDS", "3600"))  # 1 h

_hits: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def client_ip(request: Request) -> str:
    """The caller's address, trusting one proxy hop.

    Behind nginx or a load balancer every request arrives from the proxy, so
    limiting on the socket address would limit all users as one. X-Forwarded-For is
    client-controlled and only trustworthy because a proxy overwrites the leftmost
    entry it did not set — if this ever runs with no proxy in front, drop this.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce(key: str, max_attempts: int, window_seconds: int) -> None:
    """Record one attempt against `key`; raise 429 once the window is full."""
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        bucket = _hits[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= max_attempts:
            retry_after = int(bucket[0] + window_seconds - now) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Try again in a few minutes.",
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)
        # Buckets are created per key and a key is an address or an email, so an
        # attacker rotating either would otherwise grow this map without bound.
        if len(_hits) > 10_000:
            for stale in [k for k, v in _hits.items() if not v or v[-1] < cutoff]:
                del _hits[stale]


def clear() -> None:
    """Reset all counters — for tests."""
    with _lock:
        _hits.clear()
