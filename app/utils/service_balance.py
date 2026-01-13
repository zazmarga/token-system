import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Credits
from app.utils.redis_cache import get_redis
from app.core.config import config


class BalanceService:
	def __init__(self, session: AsyncSession):
		self.session = session

	@staticmethod
	def _balance_key(user_id: str) -> str:
		return f"user:{user_id}:balance"

	async def get_credits(self, user_id: str) -> Credits:
		"""Отримати кредити користувача: спочатку Redis, якщо немає — БД"""
		r = await get_redis()

		# пробуємо кеш
		cached = await r.get(self._balance_key(user_id))
		if cached:
			data = json.loads(cached)
			return Credits(
				user_id=user_id,
				balance=data["balance"],
				total_earned=data["total_earned"],
				total_spent=data["total_spent"],
			)

		# якщо немає у кеші - беремо з БД
		result = await self.session.execute(
			select(Credits).where(Credits.user_id == user_id)
		)
		credit: Credits | None = result.scalar_one_or_none()

		if not credit:
			# якщо користувач новий - створюємо пустий запис
			credit = Credits(
				user_id=user_id, balance=0, total_earned=0, total_spent=0
			)
			self.session.add(credit)
			await self.session.commit()

		# кладемо у Redis весь об’єкт як JSON
		await r.set(
			self._balance_key(user_id),
			json.dumps({
				"balance": credit.balance,
				"total_earned": credit.total_earned,
				"total_spent": credit.total_spent,
			}),
			ex=config.CACHE_TTL_SECONDS,
		)

		return credit

	async def update_credits(self, user_id: str, delta: int) -> Credits:
		"""Оновити user credits: транзакція у БД + чистка кешу"""
		async with self.session.begin_nested():
			result = await self.session.execute(
				select(Credits).where(Credits.user_id == user_id)
			)
			credit = result.scalar_one_or_none()

			if not credit:
				credit = Credits(
					user_id=user_id, balance=0, total_earned=0, total_spent=0
				)
				self.session.add(credit)

			if delta > 0:
				credit.total_earned += delta
			elif delta < 0:
				credit.total_spent += abs(delta)

			credit.balance += delta
			self.session.add(credit)

		# після commit — чистка кешу
		r = await get_redis()
		await r.delete(self._balance_key(user_id))

		return credit
