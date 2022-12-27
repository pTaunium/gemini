from sqlalchemy.sql.schema import Column, ForeignKey
from sqlalchemy.sql.sqltypes import CHAR, DATETIME, INTEGER, VARCHAR

from ._base import Base

__all__ = ["RequestSession", "RequestHeader", "RequestBody"]


class RequestSession(Base):
    __tablename__ = "request_session"

    id = Column(CHAR(32), primary_key=True)
    secret = Column(CHAR(32), nullable=False)
    exp = Column(DATETIME(), nullable=False)


class RequestHeader(Base):
    __tablename__ = "request_header"

    id = Column(INTEGER(), primary_key=True)
    session_id = Column(
        ForeignKey("request_session.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(VARCHAR(), nullable=False)
    value = Column(VARCHAR(), nullable=False)


class RequestBody(Base):
    __tablename__ = "request_body"

    id = Column(INTEGER(), primary_key=True)
    session_id = Column(
        ForeignKey("request_session.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    index = Column(INTEGER(), nullable=False)
    value = Column(VARCHAR(), nullable=False)
