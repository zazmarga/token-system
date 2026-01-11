from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str

    ADMIN_TOKEN: str
    SERVICE_TOKEN: str
    USER_TOKEN_BEARER: str

    DEBUG_MODE: bool = False

    INTERNAL_HOST: str

    REDIS_HOST: str
    REDIS_PORT: str
    REDIS_DB: int
    CACHE_TTL_SECONDS: int

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    class Config:
        env_file = ".env"


config = AppConfig()
