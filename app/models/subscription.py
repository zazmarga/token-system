from sqlalchemy import (
	Column, Integer, String, DECIMAL, Boolean, DateTime, func, ForeignKey
)
from sqlalchemy.orm import relationship, validates

from app.core.database import Base


class SubscriptionPlan(Base):
	__tablename__ = "subscription_plans"

	tier = Column(String(24), primary_key=True)
	name = Column(String(24), nullable=False, unique=True)
	monthly_cost = Column(DECIMAL(8, 2), nullable=False)
	fixed_cost = Column(DECIMAL(8, 2), nullable=False)
	credits_included = Column(Integer, nullable=False)
	bonus_credits = Column(Integer, nullable=False)
	multiplier = Column(DECIMAL(6, 2), nullable=False)
	purchase_rate = Column(DECIMAL(6, 2), nullable=False)
	active = Column(Boolean, default=True)
	created_at = Column(DateTime, server_default=func.now())
	updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

	subscriptions = relationship("Subscription", back_populates="plan")

	@validates("multiplier")
	def validate_multiplier(self, key, value):
		if value is None or value <= 0:
			raise ValueError("Multiplier must be greater than 0")
		return value

	@validates("purchase_rate")
	def validate_purchase_rate(self, key, value):
		if value is None or value < 1.0:
			raise ValueError("Purchase rate must be >= 1.0")
		return value


class Subscription(Base):
	__tablename__ = "subscriptions"

	id = Column(Integer, primary_key=True)
	user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
	plan_id = Column(String(24), ForeignKey("subscription_plans.tier"), nullable=False)
	created_at = Column(DateTime, server_default=func.now(), nullable=False)
	updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

	user = relationship("User", back_populates="subscription")
	plan = relationship("SubscriptionPlan", back_populates="subscriptions")
