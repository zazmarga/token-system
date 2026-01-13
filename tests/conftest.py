import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
	create_async_engine, AsyncSession, async_sessionmaker
)

from app.main import app
from app.core.config import config
from app.core.dependencies import get_session


# Override get_db для кожного тесту окремо
@pytest_asyncio.fixture
async def db_session():
	# Створюємо новий engine для КОЖНОГО тесту
	engine = create_async_engine(
		config.DATABASE_URL,
		echo=True,
		poolclass=None,
	)

	SessionLocal = async_sessionmaker(
		engine,
		class_=AsyncSession,
		expire_on_commit=False,
	)

	async def get_test_db():
		async with SessionLocal() as session:
			yield session

	# Override на час тесту
	app.dependency_overrides[get_session] = get_test_db

	yield  # Тест виконується тут

	# Cleanup після тесту
	app.dependency_overrides.clear()
	await engine.dispose()  #  Закриваємо engine


@pytest_asyncio.fixture
async def async_client(db_session):  # Залежить від db_session
	transport = ASGITransport(app=app)
	async with AsyncClient(transport=transport, base_url="http://test") as client:
		yield client