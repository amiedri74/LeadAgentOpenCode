import time
from collections import defaultdict
from threading import Lock
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter.
    For production with multiple instances, use Redis-based rate limiting.
    """
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.requests = defaultdict(list)
        self.lock = Lock()
    
    def _clean_old_requests(self, key: str, now: float) -> None:
        """Remove requests older than the period window."""
        self.requests[key] = [
            t for t in self.requests[key]
            if now - t < self.period
        ]
    
    def _is_rate_limited(self, key: str) -> bool:
        """Check if the key is rate limited."""
        now = time.time()
        with self.lock:
            self._clean_old_requests(key, now)
            if len(self.requests[key]) >= self.calls:
                return True
            self.requests[key].append(now)
            return False
    
    def _get_client_id(self, request: Request) -> str:
        """Get a unique identifier for the client."""
        # Use X-Forwarded-For if behind a proxy, otherwise use client host
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health check
        if request.url.path == "/api/health":
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        
        if self._is_rate_limited(client_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )
        
        return await call_next(request)
