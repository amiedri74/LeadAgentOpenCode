import time
from collections import defaultdict
from asyncio import Lock
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter(BaseHTTPMiddleware):
    """Simple in-memory rate limiter using deque with auto-eviction."""

    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _is_rate_limited(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.period

        # Evict old entries
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]

        if len(self.requests[key]) >= self.calls:
            return True
        self.requests[key].append(now)
        return False

    def _get_client_id(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/api/health":
            return await call_next(request)

        client_id = self._get_client_id(request)

        async with self._lock:
            is_limited = self._is_rate_limited(client_id)

        if is_limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )

        return await call_next(request)
