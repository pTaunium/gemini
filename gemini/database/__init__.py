import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio.engine import AsyncEngine as Engine
from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession as Session

from gemini.config import config

from ._base import Base
from .tables import *  # noqa

engine: Engine = None
logger = logging.getLogger("gemini.database")


def get_engine() -> Engine:
    global engine

    if engine is None:
        connect_args: dict[str, Any] = {}

        if config.db_url.startswith("sqlite"):
            connect_args |= {
                "check_same_thread": False,
            }

        engine = create_async_engine(
            config.db_url, connect_args=connect_args, future=True,
        )

    return engine


async def get_session(
    autocommit: bool = False, autoflush: bool = False,
) -> AsyncGenerator[Session, None]:
    engine = get_engine()
    async with Session(
        bind=engine,
        autocommit=autocommit,
        autoflush=autoflush,
        expire_on_commit=False,
        future=True,
    ) as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


scoped_session = asynccontextmanager(get_session)


async def init_db(drop: bool = False) -> None:
    engine = get_engine()

    async with engine.begin() as conn:
        if drop:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
