from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def configure_engine(url: str | None = None) -> None:
    global _engine, _sessionmaker
    url = url or get_settings().database_url
    kwargs = {} if url.startswith("sqlite") else {"pool_size": 10, "max_overflow": 10}
    _engine = create_async_engine(url, pool_pre_ping=True, **kwargs)
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)


def engine():
    if _engine is None:
        configure_engine()
    return _engine


def session_factory() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        configure_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory()() as session:
        yield session
