"""
Shared utilities used by both tabs (filler and flattener).

Keeping this in one place means both tools log in the same format,
in the same way — so the user only has to learn one log layout.
"""

import os
import logging
from datetime import datetime


def safe_filename(text: str) -> str:
    """Make a string safe to use as a filename (strips weird characters)."""
    keep = "-_.() "
    cleaned = "".join(c if c.isalnum() or c in keep else "_" for c in str(text))
    return cleaned.strip() or "record"


def setup_logger(output_dir: str, prefix: str) -> tuple[logging.Logger, str]:
    """
    Create a per-run log file in the output folder.

    Args:
        output_dir: Folder where the log file will be saved.
        prefix:     Prefix for the log filename (e.g. 'fill' or 'flatten')
                    so the user can tell which tool produced which log.

    Returns:
        (logger, log_path) — the logger object and the full path of the log file.

    The log filename is 'execution_{prefix}_YYYY-MM-DD_HH-MM-SS.log' so each
    run gets its own log without overwriting older ones.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = os.path.join(output_dir, f"execution_{prefix}_{timestamp}.log")

    # Use a unique logger name per run so handlers don't get shared between runs
    logger = logging.getLogger(f"pdf_toolkit_{prefix}_{timestamp}")
    logger.setLevel(logging.INFO)
    logger.propagate = False  # don't bubble up to the root logger
    logger.handlers.clear()   # safety against repeated runs

    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s — %(message)s",
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
