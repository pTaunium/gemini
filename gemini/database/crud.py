import secrets
import string
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio.session import AsyncSession as Session
from sqlalchemy.sql.expression import delete, select

from .tables import RequestBody, RequestHeader, RequestSession, ResponseHeader


async def create_request_session(db_session: Session) -> RequestSession:
    charts = string.ascii_letters + string.digits
    req_session = RequestSession(
        id=str(uuid4()),
        secret="".join(secrets.choice(charts) for _ in range(32)),
        exp=datetime.now() + timedelta(days=1),
    )

    db_session.add(req_session)
    await db_session.commit()
    return req_session


async def read_request_session(
    db_session: Session, req_session_id: str,
) -> RequestSession | None:
    stmt = select(RequestSession).where(
        RequestSession.id == req_session_id, RequestSession.exp > datetime.now(),
    )
    result = await db_session.execute(stmt)
    return result.scalar_one_or_none()


async def delete_request_session(db_session: Session, req_session_id: str) -> None:
    stmt = delete(RequestSession).where(
        (RequestSession.id == req_session_id) | (RequestSession.exp < datetime.now())
    )
    await db_session.execute(stmt)


async def create_request_header(
    db_session: Session, req_session_id: str, name: str, value: str,
) -> RequestHeader:
    req_header = RequestHeader(session_id=req_session_id, name=name, value=value)

    db_session.add(req_header)
    await db_session.commit()
    return req_header


async def read_request_headers(
    db_session: Session, req_session_id: str,
) -> list[RequestHeader]:
    stmt = select(RequestHeader).where(RequestHeader.session_id == req_session_id)
    result = await db_session.execute(stmt)
    return result.scalars().all()


async def create_or_update_request_body(
    db_session: Session, req_session_id: str, index: int, value: str,
) -> RequestBody:
    stmt = select(RequestBody).where(
        RequestBody.session_id == req_session_id, RequestBody.index == index
    )
    result = await db_session.execute(stmt)
    req_body: RequestBody | None = result.scalar_one_or_none()

    if req_body is None:
        req_body = RequestBody(session_id=req_session_id, index=index, value=value)
        db_session.add(req_body)
    else:
        req_body.value = value

    await db_session.commit()
    return req_body


async def read_request_bodies(
    db_session: Session, req_session_id: str,
) -> list[RequestBody]:
    stmt = (
        select(RequestBody)
        .where(RequestBody.session_id == req_session_id)
        .order_by(RequestBody.index.asc())
    )
    result = await db_session.execute(stmt)
    return result.scalars().all()


async def create_response_header(
    db_session: Session, req_session_id: str, name: str, value: str,
) -> ResponseHeader:
    resp_header = ResponseHeader(session_id=req_session_id, name=name, value=value)

    db_session.add(resp_header)
    await db_session.commit()
    return resp_header


async def read_response_headers(
    db_session: Session, req_session_id: str,
) -> list[ResponseHeader]:
    stmt = select(ResponseHeader).where(ResponseHeader.session_id == req_session_id)
    result = await db_session.execute(stmt)
    return result.scalars().all()
