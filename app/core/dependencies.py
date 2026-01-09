from fastapi import Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import config
from app.core.database import async_session


# Dependency для отримання сесії
async def get_db()-> AsyncSession:
    async with async_session() as session:
        yield session


# Dependency: перевірка адмін токену
def access_admin(x_admin_token: str = Header(...)):
    if x_admin_token != config.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")


# Dependency: перевірка internal токену
def access_internal(x_service_token: str = Header(...)):
    if x_service_token != config.SERVICE_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid service token")