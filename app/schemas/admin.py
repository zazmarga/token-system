from pydantic import BaseModel


class ExchangeRateUpdate(BaseModel):
	base_rate: int


class ExchangeRateResponse(BaseModel):
	success: bool
	old_base_rate: int
	new_base_rate: int
	updated_at: str

	class Config:
		from_attributes = True

