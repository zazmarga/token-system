from datetime import datetime

from pydantic import BaseModel


class SubscriptionPlanBase(BaseModel):
    tier: str
    name: str
    monthly_cost: float
    fixed_cost: float
    credits_included: int
    bonus_credits: int
    multiplier: float
    purchase_rate: float
    active: bool = True


class SubscriptionPlanCreate(SubscriptionPlanBase):
	pass


class SubscriptionPlanOut(SubscriptionPlanBase):
	created_at: datetime
	updated_at: datetime

	class Config:
		from_attributes = True


class SubscriptionPlanResponse(BaseModel):
	success: bool = True
	plan: SubscriptionPlanOut


class SubscriptionPlanUpdate(BaseModel):
	name: str | None = None
	monthly_cost: float | None = None
	fixed_cost: float | None = None
	credits_included: int | None = None
	bonus_credits: int | None = None
	multiplier: float | None = None
	purchase_rate: float | None = None
	active: bool | None = None
