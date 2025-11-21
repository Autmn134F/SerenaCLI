import sys
from typing import Any

def setup_logging(level: str = "INFO") -> None:
    """
    Configure logging for the wrapper.
    """
    pass

def log_error(msg: str) -> None:
    sys.stderr.write(f"ERROR: {msg}\n")

def log_info(msg: str) -> None:
    sys.stderr.write(f"INFO: {msg}\n")
