from fastapi import Header, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import config
from app.core.database import async_session
from app.utils.service_balance import BalanceService


# Dependency для отримання сесії
async def get_session()-> AsyncSession:
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


security = HTTPBearer()

# Dependency: перевірка user токену
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if token != config.USER_TOKEN_BEARER:
        raise HTTPException(status_code=403, detail="Invalid user token")
    return "user_111"  # умовний користувач, DEBUG: auth-сервісу


# Dependency: сервіс кредитів із Redis кеш
def get_balance_service(session: AsyncSession = Depends(get_session)) -> BalanceService:
    return BalanceService(session)