import redis.asyncio as redis

from app.core.config import config


# створюємо Redis клієнт
redis_client = redis.from_url(
    f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}",
    encoding="utf-8",
    decode_responses=True,
)


async def get_redis() -> redis.Redis:
    return redis_client
