import logging
import os
import threading

_basic_config_lock = threading.Lock()
_basic_config_set = False

# Loggers that are noisy at DEBUG level (polling, HTTP transport, etc.)
_QUIET_LOGGERS = [
    "uvicorn.access",
    "httpcore",
    "httpx",
    "hpack",
    "urllib3",
    "google.auth",
    "google.api_core",
    "grpc",
]


def get_logger(name: str) -> logging.Logger:
    global _basic_config_set
    with _basic_config_lock:
        if not _basic_config_set:
            log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
            logging.basicConfig(
                level=log_level,
                format='[%(asctime)s] %(levelname)s [%(name)s] - %(message)s'
            )
            for noisy in _QUIET_LOGGERS:
                logging.getLogger(noisy).setLevel(logging.WARNING)
            _basic_config_set = True
    return logging.getLogger(name)
