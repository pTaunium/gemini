from typing import Literal

from pydantic import BaseSettings

ENV = Literal["development", "production", "test"]


class Config(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    env: ENV = "development"
    debug: bool = False
    log_file: str | None = None

    secert: str = "change me"

    db_url: str = "sqlite+aiosqlite:///:memory:"
    db_debug: bool = False

    castor_url_base: str = "http://127.0.0.1:8000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


config = Config()  # load configs


if __name__ == "__main__":
    from rich.pretty import pprint

    pprint(config)
