"""
Utilities for the DHK Align backend.
Expose common logging helpers so callers can do:

    from backend.utils import logger, get_logger, configure_logging

Keeping this file ensures `backend.utils.*` resolves inside Docker/Fly.
"""
from .logger import logger, get_logger, handle  # type: ignore

try:
    handle  # type: ignore[name-defined]
except Exception:
    def handle(*_args, **_kwargs):
        """No-op log handler placeholder (overridden by real logger if present)."""
        return None

__all__ = ["logger", "get_logger", "handle"]
