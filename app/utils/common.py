from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Transaction, Settings, User


def generate_transaction_id(operation_id: str) -> str:
	# можна змінити логіку на потрібну
	return f"txn_{operation_id[3:]}"


async def is_payment_complete(payment_method_id: str) -> bool:
	# перевірка завершення сплати для поповнення кредитів користувача
	# Тут має бути якась логіка
	if payment_method_id:
		return True
	return False


async def generate_operation_id(session: AsyncSession, source: str) -> str:
	# У цьому завданні я використовую просту імітацію: лічильник у Settings
	# 	і максимальна числова частина у operation_id із transactions
	# можна змінити логіку на потрібну

	# отримати поточні settings
	settings = await session.scalar(select(Settings))
	if not settings:
		settings = Settings(current_operation_id=1)
		session.add(settings)
		await session.commit()

	# знайти максимальний номер у Transaction
	result = await session.execute(
		select(Transaction.operation_id)
	)
	ids = [row[0] for row in result.scalars().all()]
	# витягнути числа
	numbers = [int(op_id.split("_")[-1]) for op_id in ids if op_id]
	max_tx_number = max(numbers) if numbers else 0

	# обчислити новий номер
	next_number = max(settings.current_operation_id, max_tx_number + 1)

	# сформувати operation_id
	operation_id = f"op_{source}_{next_number}"

	# оновити settings
	settings.current_operation_id = next_number + 1
	await session.commit()

	return operation_id


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


async def get_base_rate_from_settings(session: AsyncSession):
	result = await session.execute(select(Settings.base_rate))
	base_rate: int | None = result.scalar()
	if not base_rate:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"База даних не містить у Settings: base_rate.",
		)
	return base_rate


def calculate_credits_amount(cost_usd: float, multiplier: float, base_rate: int) -> int:
	return round(cost_usd * multiplier * base_rate)


def dump_payload(payload):
	return payload.model_dump(exclude_unset=True, exclude_none=True)
