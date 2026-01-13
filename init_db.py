from app.core.database import engine, Base

from app.models.settings import Settings, AdminLog, AdminOperationType
from app.models.user import User
from app.models.subscription import Subscription
from app.models.credits import Credits
from app.models.transaction import Transaction


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Викликати при старті
import asyncio
asyncio.run(init_db())
