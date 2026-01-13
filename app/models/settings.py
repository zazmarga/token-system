import enum
from sqlalchemy import (
	Column, Integer, DateTime, func, String, JSON, Enum as AlchemyEnum
)

from app.core.database import Base


class Settings(Base):
	__tablename__ = "settings"

	id = Column(Integer, primary_key=True)
	base_rate = Column(Integer, default=10000)
	created_at = Column(DateTime(timezone=True), server_default=func.now())
	updated_at = Column(
		DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
	)

	# інкремент для генерації unique operation_id
	current_operation_id = Column(Integer, default=123)


# AdminLog модель зберігає зміни, що зроблено Admin у DB
class AdminOperationType(enum.Enum):
	UPDATE_BASE_RATE = "update_base_rate"
	CREATE_PLAN = "create_plan"
	UPDATE_PLAN = "update_plan"
	DELETE_PLAN = "delete_plan"
	UPDATE_MULTIPLIER = "update_multiplier"
	UPDATE_PURCHASE_RATE = "update_purchase_rate"


class AdminLog(Base):
	__tablename__ = "admin_log"

	id = Column(String, primary_key=True)
	operation_type = Column(AlchemyEnum(AdminOperationType), nullable=False)
	entity = Column(String, nullable=False)  # object: "Settings", "SubscriptionPlan", ...
	entity_id = Column(String, nullable=True)  # object_id: ID (якщо є)
	changes = Column(JSON, nullable=False)  # {"field": "base_rate", "old": 10000, "new": 12000}
	created_at = Column(DateTime(timezone=True), server_default=func.now())
