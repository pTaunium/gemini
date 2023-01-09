import asyncio
import logging
from typing import Any, AsyncGenerator

import httpx
from anyio import CapacityLimiter
from anyio.lowlevel import RunVar
from fastapi import BackgroundTasks, FastAPI
from fastapi.param_functions import Depends
from fastapi.requests import Request
from fastapi.responses import StreamingResponse

from gemini.config import config
from gemini.core.potato import Potato
from gemini.http import get_http_client
from gemini.logger import setup_logger
from gemini.utils import stream_reader

logger = logging.getLogger("gemini.pollux")
app = FastAPI(debug=config.debug)


@app.on_event("startup")
async def startup_event() -> None:
    # RunVar("_default_thread_limiter").set(CapacityLimiter(2))
    setup_logger()


@app.api_route("/{path:path}", methods=["HEAD", "GET", "POST"])
async def root_route(
    request: Request,
    background_tasks: BackgroundTasks,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> Any:
    logger.info(f"{request.method} {request.url}")

    resp = await client.get(f"{config.castor_url_base}/hello")
    session_data = resp.json()

    potato = Potato(config.secert)
    session_id = session_data["token"]
    session_secret = potato.unpack_str(session_data["data"])
    logger.info(f"{session_id=} {session_secret=}")

    potato = Potato(session_secret)
    for name, value in request.headers.items():
        if name.lower().startswith("x-forwarded"):
            continue
        if name.lower() == "accept-encoding":
            continue

        logger.info(f"Request Header: {name=} {value=}")
        potato.reset()
        encrypted_name = potato.pack_str(name)
        encrypted_value = potato.pack_str(value)
        resp = await client.get(
            f"{config.castor_url_base}/ai",
            headers={"X-CSRF-Token": session_id},
            params={"x": encrypted_name, "y": encrypted_value},
        )

    potato.reset()
    index = 0
    async for body in stream_reader(request.stream(), chunk_size=128):
        encrypted_body = potato.pack_bytes(body).decode()
        resp = await client.get(
            f"{config.castor_url_base}/ml",
            headers={"X-CSRF-Token": session_id},
            params={"i": index, "j": encrypted_body},
        )
        index += 1

    # =============================================================

    # potato.reset()
    # encrypted_method = potato.pack_str(request.method)
    # encrypted_url = potato.pack_str(str(request.url))
    # r = await client.get(
    #     f"{config.castor_url_base}/q",
    #     headers={"X-CSRF-Token": session_id},
    #     params={"m": encrypted_method, "n": encrypted_url},
    #     timeout=3600,
    # )
    # resp_json = r.json()
    # if 'data' not in resp_json:
    #     logger.error(f'{r.request.url}')
    #     logger.error(f'{resp_json=}')
    #     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # data = resp_json["data"]

    # headers: list[tuple[bytes, bytes]] = []
    # for encrypted_name, encrypted_value in data["x"]:
    #     potato.reset()
    #     name = potato.unpack_str(encrypted_name)
    #     value = potato.unpack_str(encrypted_value)
    #     logger.info(f"Response Header: {name=} {value=}")
    #     headers.append((name.lower().encode("latin-1"), value.encode("latin-1")))

    # potato.reset()
    # async def iter_body() -> AsyncGenerator[bytes, None]:
    #     for chunk in data["y"]:
    #         yield potato.unpack_bytes(chunk)
    # resp = StreamingResponse(iter_body(), status_code=data["i"])
    # resp.raw_headers = headers

    # =============================================================

    potato.reset()
    encrypted_method = potato.pack_str(request.method)
    encrypted_url = potato.pack_str(str(request.url))
    req = client.build_request(
        "GET",
        f"{config.castor_url_base}/text",
        headers={"X-CSRF-Token": session_id},
        params={"m": encrypted_method, "n": encrypted_url},
    )
    resp = await client.send(req, stream=True)

    await asyncio.sleep(0.25)
    meta_resp = await client.get(
        f"{config.castor_url_base}/home", headers={"X-CSRF-Token": session_id}
    )
    metadata = meta_resp.json().get("data", {"x": [], "i": 200})
    headers: list[tuple[bytes, bytes]] = []
    for encrypted_name, encrypted_value in metadata["x"]:
        potato.reset()
        name = potato.unpack_str(encrypted_name)
        value = potato.unpack_str(encrypted_value)
        logger.info(f"Response Header: {name=} {value=}")
        headers.append((name.lower().encode("latin-1"), value.encode("latin-1")))

    async def stream() -> AsyncGenerator[bytes, None]:
        potato.reset()
        async for chunk in resp.aiter_bytes(chunk_size=config.chunk_size * 4):
            d = potato.unpack_bytes(chunk)
            yield d

    background_tasks.add_task(resp.aclose)
    background_tasks.add_task(client.aclose)
    streaming_resp = StreamingResponse(stream(), status_code=metadata["i"])
    streaming_resp.raw_headers = headers
    return streaming_resp
