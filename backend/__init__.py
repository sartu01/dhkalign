"""
DHK Align backend package.
Keeping this file ensures `backend.*` imports resolve inside Docker and on Fly.
Expose common logging helpers at package level.
"""
try:
    from .utils.logger import logger, get_logger, configure_logging  # re-export
except Exception:
    # If logger module is unavailable for any reason, keep imports from failing.
    logger = None
    def get_logger(name=None):  # type: ignore
        return None
    def configure_logging(*args, **kwargs):  # type: ignore
        return None

__all__ = ["logger", "get_logger", "configure_logging"]
