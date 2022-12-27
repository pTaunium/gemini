import logging

import fastapi
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
        for name in ("sqlalchemy.engine", "sqlalchemy.pool"):
            logging.getLogger(name).setLevel(log_level)

    rich_handler = RichHandler()
    if config.env == "development":
        rich_handler.markup = True
        rich_handler.rich_tracebacks = True
        rich_handler.tracebacks_show_locals = True
        rich_handler.tracebacks_suppress = (
            uvicorn,
            starlette,
            fastapi,
            sqlalchemy,
            httpx,
        )
    else:
        rich_handler._log_render.omit_repeated_times = False

    logging.basicConfig(
        format=LOG_FORMAT, level=log_level, handlers=[rich_handler],
    )
