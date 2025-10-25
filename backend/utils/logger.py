import logging
from typing import Optional

_configured = False

def configure_logging(level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _configured = True

def get_logger(name: Optional[str] = None) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name or "dhkalign")

# common alias some codebases use
logger = get_logger("dhkalign")
