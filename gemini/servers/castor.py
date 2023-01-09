import asyncio
import logging
from typing import Any, AsyncGenerator

import httpx
from fastapi import BackgroundTasks, FastAPI, status
from fastapi.exceptions import HTTPException
from fastapi.param_functions import Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio.session import AsyncSession as Session

from gemini.config import config
from gemini.core.potato import Potato
from gemini.database import get_session, init_db
from gemini.database.crud import (
    create_or_update_request_body,
    create_request_header,
    create_request_session,
    create_response_header,
    delete_request_session,
    read_request_bodies,
    read_request_headers,
    read_request_session,
    read_response_headers,
)
from gemini.database.tables import RequestSession
from gemini.http import get_http_client
from gemini.logger import setup_logger

logger = logging.getLogger("gemini.castor")
app = FastAPI(debug=config.debug)


async def get_request_session(
    db_session: Session = Depends(get_session),
    x_csrf_token: str = Header(""),  # request session id
) -> RequestSession:
    for _ in range(16):
        req_session = await read_request_session(db_session, x_csrf_token)
        if req_session is not None:
            break
        await asyncio.sleep(0.1)

    else:
        logger.warning(f"{x_csrf_token=}")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="QQ Not Found")

    return req_session


@app.on_event("startup")
async def startup_event() -> None:
    setup_logger()
    await init_db()


@app.get("/hello")
async def ask_new_request_session(db_session: Session = Depends(get_session)) -> Any:
    req_session = await create_request_session(db_session)

    potato = Potato(config.secert)
    return {
        "result": 1,
        "token": req_session.id,
        "data": potato.pack_str(req_session.secret),
    }


@app.get("/ai")
async def add_header(
    db_session: Session = Depends(get_session),
    req_session: RequestSession = Depends(get_request_session),
    x: str = Query(...),  # encrypted_name
    y: str = Query(...),  # encrypted_value
) -> Any:
    potato = Potato(req_session.secret)
    name = potato.unpack_str(x)
    value = potato.unpack_str(y)
    logger.info(f"[{req_session.id}] Add Header - {name=} {value=}")

    await create_request_header(db_session, req_session.id, name, value)

    return {"result": 1, "data": []}


@app.get("/ml")
async def add_body(
    db_session: Session = Depends(get_session),
    req_session: RequestSession = Depends(get_request_session),
    i: int = Query(..., min=0),  # index
    j: str = Query(...),  # encrypted_body
) -> Any:
    logger.info(f"[{req_session.id}] Add Body - {i=} {j=}")

    await create_or_update_request_body(db_session, req_session.id, i, j)

    return {"result": 1, "data": []}


@app.get("/text")
async def do_request(
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(get_session),
    client: httpx.AsyncClient = Depends(get_http_client),
    req_session: RequestSession = Depends(get_request_session),
    m: str = Query(...),  # encrypted_method
    n: str = Query(...),  # encrypted_url
) -> Any:
    potato = Potato(req_session.secret)
    method = potato.unpack_str(m)
    url = potato.unpack_str(n)

    headers: list[tuple[str, str]] = []
    for req_header in await read_request_headers(db_session, req_session.id):
        if req_header.name.lower() == "accept-encoding":
            headers.append(("accept-encoding", ""))
        else:
            headers.append((req_header.name, req_header.value))

    potato.reset()
    body = b""
    for req_body in await read_request_bodies(db_session, req_session.id):
        body += potato.unpack_bytes(req_body.value.encode())

    logger.info(f"[{req_session.id}] Do Request - {method} {url}\n{headers=}\n{body=}")

    req = client.build_request(method, url, headers=headers, content=body)
    resp = await client.send(req, stream=True)

    await create_response_header(
        db_session, req_session.id, "@@status_code", str(resp.status_code)
    )

    for name, value in resp.headers.items():
        logger.info(f"Response Header: {name=} {value=}")
        await create_response_header(db_session, req_session.id, name, value)

    async def stream() -> AsyncGenerator[bytes, None]:
        potato.reset()
        async for chunk in resp.aiter_bytes(chunk_size=config.chunk_size * 3):
            yield potato.pack_bytes(chunk)

    background_tasks.add_task(resp.aclose)
    background_tasks.add_task(delete_request_session, db_session, req_session.id)
    return StreamingResponse(stream(), media_type="text/plain")


@app.get("/home")
async def get_response_headers(
    db_session: Session = Depends(get_session),
    req_session: RequestSession = Depends(get_request_session),
) -> Any:
    potato = Potato(req_session.secret)
    status_code = 200
    headers: list[tuple[str, str]] = []
    for header in await read_response_headers(db_session, req_session.id):
        name = header.name
        value = header.value
        logger.debug(f"Response Header: {name=} {value=}")
        if name == "@@status_code":
            try:
                status_code = int(value)
            except:
                pass
        else:
            potato.reset()
            headers.append((potato.pack_str(name), potato.pack_str(value)))

    return {
        "result": 1,
        "data": {"x": headers, "i": status_code},
    }
