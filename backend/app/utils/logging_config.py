import logging
import sys


def setup_logging() -> None:
    """Configure application-wide logging."""

    root_logger = logging.getLogger()
    if root_logger.handlers:
        # Already configured
        return

    root_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s"
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

