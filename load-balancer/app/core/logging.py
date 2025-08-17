"""Logging configuration utilities for the Load Balancer service."""
import logging
import os


def setup_logging() -> None:
    """Configure root logging based on the LOG_LEVEL environment variable."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
