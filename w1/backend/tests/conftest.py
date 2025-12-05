import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool
from app.database import Base

# 测试数据库 URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/project_alpha_test"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    # Create engine with NullPool to avoid connection issues
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session

    # Cleanup: drop all data and close
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
