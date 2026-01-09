from typing import Optional

from pydantic import BaseModel, Field

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


class CreditsAddRequest(BaseModel):
	user_id: str
	amount_usd: float = Field(..., gt=0)
	source: str
	operation_id: str
	description: str
	metadata: dict


class CreditsAddResponse(BaseModel):
	success: bool = True
	transaction_id: str
	user_id: str
	amount_usd: float
	credits_added: int
	purchase_rate: float
	balance_before: int
	balance_after: int
	operation_id: str
