from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
	__tablename__ = "user"

	id = Column(Integer, primary_key=True, index=True)
	subscription_tier = Column(
		String,
		ForeignKey("subscription_plans.tier", ondelete="RESTRICT"),
		nullable=True
	)
	# ORM-зв’язок
	subscription = relationship("SubscriptionPlan", back_populates="users")

	@property
	def public_id(self) -> str:
		return f"user_{self.id}"
