from pydantic import BaseModel

from app.schemas.subscription import SubscriptionPlanInternal


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
