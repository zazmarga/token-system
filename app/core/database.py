from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import config


engine = create_async_engine(config.DATABASE_URL, echo=config.DEBUG_MODE)  # echo=True для debug (!)
async_session=sessionmaker(
	bind=engine,
	expire_on_commit=False,
	class_=AsyncSession
)

Base = declarative_base()
