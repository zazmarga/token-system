from datetime import datetime
from typing import Dict

from pydantic import BaseModel


# Statistics Admin
class StatisticsPeriod(BaseModel):
	start: datetime
	end: datetime


class StatisticsPlans(BaseModel):
	subscriptions: Dict[str, int]


class StatisticsCredits(BaseModel):
	total_earned: int
	total_spent: int
	current_balance: int


class StatisticsTransactions(BaseModel):
	total: int
	charges: int
	additions: int


class StatisticsResponse(BaseModel):
	period: StatisticsPeriod
	total_users: int
	subscriptions: StatisticsPlans
	credits: StatisticsCredits
	transactions: StatisticsTransactions


# problem: circular import
class UserCreditsBase(BaseModel):
	balance: int
	total_earned: int
	total_spent: int

	class Config:
		from_attributes = True
