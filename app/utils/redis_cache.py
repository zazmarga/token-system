import redis.asyncio as redis

from app.core.config import config


# створюємо клієнт
redis_client = redis.from_url(
    f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}",
    encoding="utf-8",
    decode_responses=True,
)


async def cache_set_balance(user_id: str, value: str):
	key = balance_key(user_id)
	await redis_client.set(key, value, ex=config.CACHE_TTL_SECONDS)


async def cache_get_balance(user_id: str) -> int | None:
	key = balance_key(user_id)
	val = await redis_client.get(key)
	return int(val) if val is not None else None


async def cache_delete_balance(user_id: str):
	key = balance_key(user_id)
	return await redis_client.delete(key)


def balance_key(user_id: str) -> str:
	return f"user:{user_id}:balance"
