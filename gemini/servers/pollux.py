import logging
from typing import Any, AsyncGenerator

import httpx
from fastapi import FastAPI
from fastapi.param_functions import Depends
from fastapi.requests import Request
from fastapi.responses import Response, StreamingResponse

from gemini.config import config
from gemini.core.potato import Potato
from gemini.http import get_http_client
from gemini.logger import setup_logger
from gemini.utils import stream_reader

logger = logging.getLogger("gemini.pollux")
app = FastAPI(debug=config.debug)


@app.on_event("startup")
async def startup_event() -> None:
    setup_logger()


@app.api_route("/{path:path}", methods=["GET", "POST"])
async def root_route(
    request: Request, client: httpx.AsyncClient = Depends(get_http_client),
) -> Any:
    logger.info(f"Method: {request.method}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Headers: {request.headers}")

    r = await client.get(f"{config.castor_url_base}/ks")
    data = r.json()

    potato = Potato(config.secert)
    session_id = data["token"]
    session_secret = potato.unpack_str(data["data"])
    logger.info(f"{session_id=} {session_secret=}")

    potato = Potato(session_secret)
    for name, value in request.headers.items():
        logger.info(f"Header: {name=} {value=}")
        potato.reset()
        encrypted_name = potato.pack_str(name)
        encrypted_value = potato.pack_str(value)
        r = await client.get(
            f"{config.castor_url_base}/ai",
            headers={"X-CSRF-Token": session_id},
            params={"x": encrypted_name, "y": encrypted_value},
        )

    potato.reset()
    index = 0
    async for body in stream_reader(request.stream(), chunk_size=128):
        encrypted_body = potato.pack_bytes(body)
        r = await client.get(
            f"{config.castor_url_base}/ml",
            headers={"X-CSRF-Token": session_id},
            params={"i": index, "j": encrypted_body},
        )
        index += 1

    potato.reset()
    encrypted_method = potato.pack_str(request.method)
    encrypted_url = potato.pack_str(str(request.url))
    r = await client.get(
        f"{config.castor_url_base}/q",
        headers={"X-CSRF-Token": session_id},
        params={"m": encrypted_method, "n": encrypted_url},
    )
    data = r.json()["data"]

    headers = {}
    for encrypted_name, encrypted_value in data["x"]:
        potato.reset()
        name = potato.unpack_str(encrypted_name)
        value = potato.unpack_str(encrypted_value)
        headers[name] = value

    potato.reset()

    async def iter_body() -> AsyncGenerator[bytes, None]:
        for chunk in data["y"]:
            yield potato.unpack_bytes(chunk)

    return StreamingResponse(iter_body(), status_code=data["i"], headers=headers)
