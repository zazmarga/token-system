from logging.config import fileConfig
from sqlalchemy import pool

from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import config as app_config

from alembic import context

from app.core.database import Base
from app.models import *


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    url = app_config.DATABASE_URL

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    from sqlalchemy.ext.asyncio import create_async_engine
    import asyncio

    connectable = create_async_engine(app_config.DATABASE_URL, poolclass=pool.NullPool)

    async def do_run_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(
                lambda sync_conn: context.configure(
                    connection=sync_conn,
                    target_metadata=target_metadata,
                )
            )
            await connection.run_sync(lambda sync_conn: context.run_migrations())

    asyncio.run(do_run_migrations())



if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
