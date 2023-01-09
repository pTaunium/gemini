import logging
import sys

import fastapi
import h11
import httpx
import sqlalchemy
import starlette
import uvicorn
from rich.logging import RichHandler

from gemini.config import config

LOG_FORMAT = "%(name)s - %(message)s"


def setup_logger() -> None:
    log_level = logging.INFO
    if config.debug:
        log_level = logging.DEBUG

    # Remove all handlers from root logger
    # and propagate to root logger.
    for name in logging.root.manager.loggerDict.keys():
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True

    if config.db_debug:
        for name in ("sqlalchemy.engine", "sqlalchemy.pool", "aiosqlite"):
            logging.getLogger(name).setLevel(log_level)
    else:
        for name in ("sqlalchemy.engine", "sqlalchemy.pool", "aiosqlite"):
            logging.getLogger(name).setLevel(logging.WARNING)

    handlers: list[logging.Handler] = []
    if config.env == "development":
        log_format = "%(name)s - %(message)s"
        date_format = "[%x %X]"
        rich_handler = RichHandler(
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            tracebacks_suppress=(uvicorn, starlette, fastapi, sqlalchemy, h11, httpx),
            log_time_format=date_format,
        )
        rich_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(rich_handler)
    else:
        log_format = "%(asctime)s %(levelname)-8s %(name)s - %(message)s"
        date_format = "[%x %X]"
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(
            logging.Formatter(fmt=log_format, datefmt=date_format)
        )
        handlers.append(stream_handler)

    logging.basicConfig(level=log_level, handlers=handlers)
