from typing import Optional

from pydantic import BaseModel

from app.schemas.subscription import SubscriptionPlanInternal


# Internal
class CreditsBase(BaseModel):
	balance: int
	total_earned: int
	total_spent: int

	class Config:
		from_attributes = True


class CreditsUserBalanceResponse(BaseModel):
	user_id: str
	subscription: SubscriptionPlanInternal
	credits: CreditsBase


class CreditsUserCheckResponse(BaseModel):
	user_id: str
	has_subscription: bool
	subscription_tier: Optional[str] = None
	balance: int
	sufficient: bool
	multiplier: float
