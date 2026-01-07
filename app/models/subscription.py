from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, func

from app.core.database import Base


class SubscriptionPlan(Base):
	__tablename__ = "subscription_planes"

	tier = Column(String(24), primary_key=True)
	name =  Column(String(24), nullable=False, unique=True)
	monthly_cost = Column(DECIMAL(8, 2), nullable=False)
	fixed_cost = Column(DECIMAL(8, 2), nullable=False)
	credits_included = Column(Integer, nullable=False)
	bonus_credits = Column(Integer, nullable=False)
	multiplier = Column(DECIMAL(6, 2), nullable=False)
	purchase_rate = Column(DECIMAL(6, 2), nullable=False)
	active = Column(Boolean, default=True)
	created_at = Column(DateTime, server_default=func.now())
	updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Subscription(Base):
	__tablename__ = "subscriptions"

	id = Column(Integer, primary_key=True)
