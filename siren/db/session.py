from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from functools import lru_cache
from .models import Base


@lru_cache(maxsize=1)
def _get_engine(database_url: str):
    return create_async_engine(database_url, echo=False, pool_pre_ping=True)


def get_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = _get_engine(database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_tables(database_url: str) -> None:
    engine = _get_engine(database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
