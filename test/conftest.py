from datetime import date, datetime
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config import settings
from src.db.connection import get_async_session
from src.models import Base, SubjectsORM
from src.main import app

test_engine = create_async_engine(
    settings.DATABASE_URL_TEST,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False
)

TestingAsyncSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="function", autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingAsyncSessionLocal() as session:
        await session.begin_nested()
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture(scope="function")
async def async_client():
    app.dependency_overrides[get_async_session] = override_get_async_session

    async with AsyncClient(transport=ASGITransport(app), base_url='http://test') as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_subject(db_session):
    async with db_session as session:
        result = await session.execute(
            insert(SubjectsORM).values(
                weight=100,
                length=150
            ).returning(SubjectsORM.id)
        )
        subject_id = result.scalar_one()
        await session.commit()

        return subject_id


@pytest.fixture
async def test_subjects_for_get(db_session):
    async with db_session as session:
        await session.execute(
            insert(SubjectsORM).values([
                {"weight": 11, "length": 21, "is_active": True,
                 'create_at': date(2026, 12, 1)},
                {"weight": 12, "length": 22, "is_active": False,
                 "delete_at": datetime(2026, 12, 10), 'create_at': date(2026, 12, 7)},
                {"weight": 13, "length": 23, "is_active": True,
                 'create_at': date(2026, 12, 1)},
                {"weight": 12, "length": 22, "is_active": False,
                 "delete_at": datetime(2026, 12, 11), 'create_at': date(2026, 12, 8)},
                {"weight": 12, "length": 22, "is_active": False,
                 "delete_at": datetime(2026, 12, 12), 'create_at': date(2026, 12, 9)},
            ]
            )
        )
        await session.commit()


async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingAsyncSessionLocal() as session:
        await session.begin_nested()  # Изолируем транзакции тестов
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()
