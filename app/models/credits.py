from sqlalchemy import Column, Integer

from app.core.database import Base


class Credits(Base):
	__tablename__ = "credits"

	id = Column(Integer, primary_key=True)
