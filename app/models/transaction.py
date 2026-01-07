from sqlalchemy import Column, Integer

from app.core.database import Base


class Transaction(Base):
	__tablename__ = "transactions"

	id = Column(Integer, primary_key=True)
