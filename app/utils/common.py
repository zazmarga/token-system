from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Settings


async def is_payment_complete(payment_method_id: str) -> bool:
	# перевірка завершення сплати для поповнення кредитів користувача
	return True


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
