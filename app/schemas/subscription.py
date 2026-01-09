from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, computed_field


#  Admin endpoints
class SubscriptionPlanBase(BaseModel):
	tier: str
	name: str
	monthly_cost: float
	fixed_cost: float
	credits_included: int
	bonus_credits: int
	multiplier: float
	purchase_rate: float

	class Config:
		from_attributes = True


class SubscriptionPlanCreate(SubscriptionPlanBase):
	active: bool


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


# Public endpoints
class SubscriptionPlanPublicDetail(SubscriptionPlanBase):
	@computed_field
	@property
	def total_credits(self) -> int:
		return self.credits_included + self.bonus_credits


class SubscriptionPlanPublicList(BaseModel):
	plans: List[SubscriptionPlanPublicDetail]


# Internal endpoints
class SubscriptionUpdateRequest(BaseModel):
	user_id: str
	subscription_tier: str
	credits_to_add: int
	operation_id: str


class SubscriptionUpdateResponse(BaseModel):
	success: bool = True
	user_id: str
	previous_tier: Optional[str] = None
	new_tier: str
	credits_added: int
	new_balance: int
	multiplier: float
	purchase_rate: float


class SubscriptionPlanInternal(BaseModel):
	tier: Optional[str] = None
	monthly_cost: float
	multiplier: float
	purchase_rate: float
