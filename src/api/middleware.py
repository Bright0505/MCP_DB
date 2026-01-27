"""API middleware for rate limiting and security."""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI
from src.core.config import HTTPConfig


# Create rate limiter instance with configurable default limit
_http_config = HTTPConfig.from_env()
limiter = Limiter(key_func=get_remote_address, default_limits=[_http_config.rate_limit_default])


def setup_rate_limiting(app: FastAPI):
    """
    Configure rate limiting for FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
