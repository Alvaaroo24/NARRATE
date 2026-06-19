from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from contextlib import asynccontextmanager

from imc.config import settings
from imc.modules.utils import custom_logs

logger = custom_logs.getLogger(__name__)


engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
)


async_session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False, class_=AsyncSession
)

Base = declarative_base()


@asynccontextmanager
async def make_session():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_db_async() -> AsyncGenerator[AsyncSession, None]:
    """Get database async session

    Yields:
        AsyncSession
    """
    async with make_session() as session:
        yield session
