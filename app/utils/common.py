from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Settings, User, Credits


def generate_transaction_id(operation_id: str) -> str:
	# можна змінити логіку на потрібну
	return f"txn_{operation_id[3:]}"


async def is_payment_complete(payment_method_id: str) -> bool:
	# перевірка завершення сплати для поповнення кредитів користувача
	# Тут має бути якась логіка
	if payment_method_id:
		return True
	return False


async def generate_operation_id(db: AsyncSession, source: str) -> str:
	# У цьому завданні я використовую простий лічильник у Settings.
	# У реальному середовищі треба додати механізм захисту від конкурентних запитів

	# отримуємо Settings
	settings = await db.scalar(select(Settings))
	if not settings:
		settings = Settings()
		db.add(settings)
		await db.commit()

	# беремо поточний номер
	op_number = settings.current_operation_id

	# формуємо operation_id
	operation_id = f"op_{source}_{op_number}"

	# збільшуємо на 1
	settings.current_operation_id += 1
	await db.commit()

	return operation_id


async def user_existing_check(db: AsyncSession, user_id: str):
	"""
	Перевіряє, чи користувач існує в базі даних.
	Якщо ні, генерує виняток.
	"""
	user = await db.get(User, user_id)
	if not user:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"User '{user_id}' not found.",
		)


async def get_base_rate_from_settings(db: AsyncSession):
	result = await db.execute(select(Settings.base_rate))
	base_rate: int | None = result.scalar()
	if not base_rate:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"База даних не містить у Settings: base_rate.",
		)
	return base_rate


async def get_user_balance(db: AsyncSession, user_id: str) -> int:
	result = await db.execute(select(Credits.balance).where(Credits.user_id == user_id))
	user_balance = result.scalar_one()
	return user_balance


def calculate_credits_amount(cost_usd: float, multiplier: float, base_rate: int) -> int:
	return round(cost_usd * multiplier * base_rate)