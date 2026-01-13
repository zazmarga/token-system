from typing import Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Settings, User, SubscriptionPlan


def generate_transaction_id(operation_id: str) -> str:
	# можна змінити логіку на потрібну
	return f"txn_{operation_id[3:]}"


async def is_payment_complete(payment_method_id: str) -> bool:
	# перевірка завершення сплати для поповнення кредитів користувача
	# Тут має бути якась логіка
	if payment_method_id:
		return True
	return False


async def get_base_rate_from_settings(
		session: AsyncSession, created: bool = False
) -> Tuple[int, bool, Settings]:
	result = await session.execute(select(Settings))
	settings = result.scalar_one_or_none()

	if not settings:
		created = True
		settings = Settings(base_rate=10000)  # дефолтне значення
		session.add(settings)
		await session.flush()

	return (settings.base_rate, created, settings)


async def user_existing_check(session: AsyncSession, user_id: str):
	"""
	Перевіряє, чи користувач існує в базі даних.
	Якщо ні, генерує виняток.
	"""
	user = await session.get(User, user_id)
	if not user:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"User '{user_id}' not found.",
		)


async def tier_existing_check(session: AsyncSession, tier: str):
	"""
	Перевіряє, чи tier існує в базі даних.
	Якщо ні, генерує виняток.
	"""
	ex_tier = await session.get(SubscriptionPlan, tier)
	if not ex_tier:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"Subscription Plan '{tier}' not found.",
		)


def calculate_credits_amount(cost_usd: float, multiplier: float, base_rate: int) -> int:
	return round(cost_usd * multiplier * base_rate)


def dump_payload(payload):
	return payload.model_dump(exclude_unset=True, exclude_none=True)
