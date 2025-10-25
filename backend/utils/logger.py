import logging
from typing import Optional

__all__ = ("configure_logging", "get_logging_level", "set_logging_level", "logger", "get_logger", "handle")

_configured = False

def get_logging_level() -> int:
    """Return current root logging level (defaults to logging.INFO)."""
    return logging.getLogger().level or logging.INFO

def set_logging_level(level: int | str) -> None:
    """Set root logging level. Accepts int or names like 'INFO', 'DEBUG'."""
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    logging.getLogger().setLevel(level)  # affects subsequent getLogger() calls

def configure_logging(level: int = logging.INFO) -> None:
    """Idempotently configure a basic stream handler with a sane format."""
    global _configured
    if _configured:
        return
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        handler.setFormatter(fmt)
        root.addHandler(handler)
    root.setLevel(level)
    _configured = True

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger, ensuring base config is applied once."""
    configure_logging(get_logging_level())
    return logging.getLogger(name or "dhkalign")

# Common alias some codebases use
logger = get_logger("dhkalign")

def handle(exc: BaseException, msg: Optional[str] = None, *, level: int = logging.ERROR, lg: Optional[logging.Logger] = None) -> None:
    """Log an exception safely.

    If called inside an exception handler, will include traceback via logger.exception().
    If called outside an exception context, falls back to logger.log(level,...).
    """
    log = lg or get_logger()
    # If we're in an active exception context, logger.exception will include traceback
    if level >= logging.ERROR:
        if msg:
            log.exception(msg)
        else:
            log.exception(str(exc))
    else:
        log.log(level, f"{msg or str(exc)}")
