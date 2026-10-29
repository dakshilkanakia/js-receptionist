import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

# Tests run each case in its own event loop, so they can't share pooled connections.
_pool = {"poolclass": NullPool} if os.getenv("DB_NULLPOOL") == "1" else {"pool_pre_ping": True}
engine = create_async_engine(settings.database_url, **_pool)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
