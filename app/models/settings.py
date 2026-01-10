from sqlalchemy import Column, Integer, DateTime, func

from app.core.database import Base


class Settings(Base):
	__tablename__ = "settings"

	id = Column(Integer, primary_key=True)
	base_rate = Column(Integer, default=10000)  # $1 = 10,000 credits
	created_at = Column(DateTime(timezone=True), server_default=func.now())
	updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

	# інкремент для генерації unique operation_id
	current_operation_id = Column(Integer, default=123)
