#!/usr/bin/env python3

import argparse
import logging

import uvicorn

from gemini.config import config
from gemini.logger import setup_logger


def main() -> None:
    setup_logger()

    parser = argparse.ArgumentParser()
    parser.add_argument("server", help="server name", choices=["castor", "pollux"])
    args = parser.parse_args()

    uvicorn.run(
        f"gemini.servers.{args.server}:app",
        host=config.host,
        port=config.port,
        log_level=logging.DEBUG if config.debug else logging.INFO,
        reload=True if config.env == "development" else False,
        reload_dirs=["gemini"],
        workers=1,
        log_config=None,
        proxy_headers=True,
    )


if __name__ == "__main__":
    main()
