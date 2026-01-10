from pydantic import BaseModel


# circular import problem
class UserCreditsBase(BaseModel):
	balance: int
	total_earned: int
	total_spent: int

	class Config:
		from_attributes = True