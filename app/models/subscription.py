from sqlalchemy import Column, Integer

from app.core.database import Base


class Subscription(Base):
	__tablename__ = "subscriptions"

	id = Column(Integer, primary_key=True)
