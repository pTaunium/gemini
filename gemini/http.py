import logging
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)


async def get_http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(timeout=60) as client:
        yield client
