"""Structured application logging.

Deliberately minimal: a console handler with a stable format. Secrets, passwords,
tokens, uploaded media contents and full request bodies are never logged.
"""

import logging
import sys

_CONFIGURED = False

_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once per process."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger for a module, ensuring logging is configured."""
    configure_logging()
    return logging.getLogger(name)
