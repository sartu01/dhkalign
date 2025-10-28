from __future__ import annotations

import asyncio
import logging
import time
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, Optional

__all__ = (
    "logger",
    "configure_logging",
    "get_logger",
    "log_startup",
    "log_shutdown",
    "log_execution_time",
    "log_api_request",
    "log_health_check",
    "LogAnalyzer",
)


class AppLogger(logging.Logger):
    """Custom logger that adds helpers for structured database logging."""

    def database_operation(self, op: str, success: bool, **kw: Any) -> None:
        payload = {"op": op, "success": bool(success)}
        payload.update(kw)
        self.info("db_op", extra=payload)


if logging.getLoggerClass() is not AppLogger:
    logging.setLoggerClass(AppLogger)

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging once with a basic stream handler."""
    global _CONFIGURED
    root = logging.getLogger()
    if not _CONFIGURED:
        if not root.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(level)
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
            root.addHandler(handler)
        _CONFIGURED = True
    root.setLevel(level)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a configured logger instance."""
    configure_logging(logging.INFO)
    return logging.getLogger(name or "dhkalign")


logger = get_logger("dhkalign")


def _duration_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000.0


def log_startup(msg: str) -> None:
    logger.info(msg, extra={"phase": "startup"})


def log_shutdown(msg: str) -> None:
    logger.info(msg, extra={"phase": "shutdown"})


def log_health_check(status: str, **kw: Any) -> None:
    payload = {"status": status}
    payload.update(kw)
    logger.info("health_check", extra=payload)


def log_execution_time(_logger: logging.Logger, op_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to log duration for sync or async callables."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(fn):

            @wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.perf_counter()
                try:
                    return await fn(*args, **kwargs)
                finally:
                    _logger.info("timing", extra={"op": op_name, "duration_ms": _duration_ms(start)})

            return async_wrapper

        @wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                _logger.info("timing", extra={"op": op_name, "duration_ms": _duration_ms(start)})

        return sync_wrapper

    return decorator


def log_api_request(_logger: logging.Logger) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Decorator for async route handlers to log request/response metadata."""

    def decorator(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        if not asyncio.iscoroutinefunction(fn):

            @wraps(fn)
            async def async_adapter(*args: Any, **kwargs: Any) -> Any:
                return fn(*args, **kwargs)

            target = async_adapter
        else:
            target = fn

        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = kwargs.get("request")
            if request is None:
                for arg in args:
                    if hasattr(arg, "method") and hasattr(arg, "url"):
                        request = arg
                        break

            method = getattr(request, "method", None)
            path = None
            if request is not None:
                try:
                    path = request.url.path  # type: ignore[attr-defined]
                except Exception:
                    path = None

            try:
                response = await target(*args, **kwargs)
            except Exception:
                _logger.exception(
                    "api_request",
                    extra={"method": method, "path": path, "status": 500, "ok": False},
                )
                raise

            status = getattr(response, "status_code", 200)
            try:
                status_int = int(status)
            except Exception:
                status_int = 500

            _logger.info(
                "api_request",
                extra={"method": method, "path": path, "status": status_int, "ok": status_int < 500},
            )
            return response

        return wrapper

    return decorator


class LogAnalyzer:
    """Minimal analyzer interface expected by the application."""

    def get_translation_stats(self, hours: int = 24) -> Dict[str, Any]:
        return {
            "total_requests": 0,
            "successful_translations": 0,
            "avg_processing_time_ms": 0,
            "methods_used": {},
            "window_hours": hours,
        }

    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        return {"errors": 0, "by_type": {}, "window_hours": hours}
