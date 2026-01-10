from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.subscription import SubscriptionPlanInternal


# **************    Internal
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


class CreditsCalculateRequest(BaseModel):
	user_id: str
	cost_usd: float


class CreditsCalculateResponse(CreditsCalculateRequest):
	credits_to_charge: int
	multiplier: float
	current_balance: Optional[int] = 0
	balance_after: Optional[int] = 0
	sufficient: bool


class CreditsChargeRequest(CreditsCalculateRequest):
	operation_id: str
	description: str
	metadata: dict


class CreditsChargeNoSuccessResponse(BaseModel):
	success: bool = False
	error: str
	user_id: str
	required_credits: int
	current_balance: int
	deficit: int


class CreditsChargeSuccessResponse(BaseModel):
	success: bool = True
	transaction_id: str
	user_id: str
	cost_usd: float
	credits_charged: int
	balance_before: int
	balance_after: int
	operation_id: str


# **************    Public
class CreditsPurchasePayload(BaseModel):
	amount_usd: float
	payment_method_id: str


class CreditsPurchaseResponse(BaseModel):
	success: bool
	transaction_id: str
	amount_usd: float
	credits_added: int
	new_balance: int
