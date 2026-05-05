"""
Shared utilities for both tabs.

Key idea: ONE parent folder per project. Inside it:
  ├── filled_pdfs/      <- Tab 1 writes here
  ├── flattened_pdfs/   <- Tab 2 writes here
  └── execution.log     <- both tabs append timestamped entries here

Why one log? You only need to look in one place to see what happened.
Why append-mode? You keep the full history if you re-run a step.
"""

import os
import logging
from datetime import datetime


# Constants shared by both tabs — keeps folder names consistent.
FILLED_SUBFOLDER = "filled_pdfs"
FLATTENED_SUBFOLDER = "flattened_pdfs"
LOG_FILENAME = "execution.log"


def safe_filename(text: str) -> str:
    """Make a string safe to use as a filename (strips weird characters)."""
    keep = "-_.() "
    cleaned = "".join(c if c.isalnum() or c in keep else "_" for c in str(text))
    return cleaned.strip() or "record"


def ensure_subfolder(parent_dir: str, subfolder: str) -> str:
    """
    Make sure a subfolder exists inside the parent folder.
    Returns the full path to the subfolder.
    """
    full_path = os.path.join(parent_dir, subfolder)
    os.makedirs(full_path, exist_ok=True)
    return full_path


def setup_logger(parent_dir: str, run_tag: str) -> tuple[logging.Logger, str]:
    """
    Create a logger that APPENDS to the shared 'execution.log' in the parent
    folder.

    Args:
        parent_dir: The project folder (where filled_pdfs/ and flattened_pdfs/
                    live).
        run_tag:    A short tag like 'FILL' or 'FLATTEN' that gets prefixed
                    to every log line so you can tell which run produced it.

    Returns (logger, log_path).
    """
    log_path = os.path.join(parent_dir, LOG_FILENAME)

    # Each run gets a unique logger name (so handlers don't get mixed between runs)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger_name = f"pdf_toolkit_{run_tag}_{timestamp}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    # mode='a' = APPEND, so older runs are kept
    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    formatter = logging.Formatter(
        fmt=f"[%(asctime)s] [{run_tag}] %(levelname)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger, log_path


def close_logger(logger: logging.Logger) -> None:
    """Close all file handlers and detach them so the log file is flushed."""
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
