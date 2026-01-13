from datetime import datetime
from typing import List, Optional, Literal, Union

from pydantic import (
	BaseModel, Field, field_serializer, ConfigDict, computed_field
)


class TransactionBase(BaseModel):
	id: str
	created_at: datetime = Field(exclude=True)
	credits: int
	balance_after: int
	description: Optional[str] = None
	operation_id: str

	@computed_field
	@property
	def date(self) -> datetime:
		return self.created_at

	model_config = ConfigDict(
		from_attributes=True,
		use_enum_values = True
	)


# списання (витрата)
class ChargeTransaction(TransactionBase):
	type: Literal["charge"]
	cost_usd: Optional[float] = None

	@field_serializer("cost_usd")
	def format_amount(self, v: Optional[float], _info):
		if v is None:
			return None
		return float(round(v, 4)) # 4 знаки після крапки


# поповнення
class AddTransaction(TransactionBase):
	type: Literal["add"]
	amount_usd: Optional[float] = None

	@field_serializer("amount_usd")
	def format_amount(self, v: Optional[float], _info):
		if v is None:
			return None
		return float(round(v, 2)) # 2 знаки після крапки


# нарахування при підписці
class SubscriptionTransaction(TransactionBase):
	type: Literal["subscription"]


TransactionDetail = Union[ChargeTransaction, AddTransaction, SubscriptionTransaction]


class TransactionPublicPaginatedList(BaseModel):
	total: int
	limit: int
	offset: int
	transactions: List[TransactionDetail]
