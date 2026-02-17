import logging
import os
import threading

_basic_config_lock = threading.Lock()
_basic_config_set = False

def get_logger(name: str) -> logging.Logger:
    global _basic_config_set
    with _basic_config_lock:
        if not _basic_config_set:
            log_level = os.getenv("LOG_LEVEL", "INFO").upper()
            logging.basicConfig(
                level=log_level,
                format='[%(asctime)s] %(levelname)s [%(name)s] - %(message)s'
            )
            _basic_config_set = True
    return logging.getLogger(name)
