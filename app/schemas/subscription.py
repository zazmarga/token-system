from datetime import datetime
from typing import List

from pydantic import BaseModel, computed_field


class SubscriptionPlanBase(BaseModel):
	tier: str
	name: str
	monthly_cost: float
	fixed_cost: float
	credits_included: int
	bonus_credits: int
	multiplier: float
	purchase_rate: float
	# active: bool = True

	class Config:
		from_attributes = True


class SubscriptionPlanCreate(SubscriptionPlanBase):
	pass


class SubscriptionPlanOut(SubscriptionPlanBase):
	active: bool
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


class SubscriptionPlanDetail(SubscriptionPlanOut):
	users_count: int


class SubscriptionPlanList(BaseModel):
	plans: List[SubscriptionPlanDetail]


class MultiplierUpdateResponse(BaseModel):
	success: bool = True
	tier: str
	old_multiplier: float
	new_multiplier: float
	updated_at: datetime


class PurchaseRateUpdateResponse(BaseModel):
	success: bool = True
	tier: str
	old_purchase_rate: float
	new_purchase_rate: float
	updated_at: datetime


class SubscriptionPlanPublicDetail(SubscriptionPlanBase):
	@computed_field
	@property
	def total_credits(self) -> int:
		return self.credits_included + self.bonus_credits


class SubscriptionPlanPublicList(BaseModel):
	plans: List[SubscriptionPlanPublicDetail]
