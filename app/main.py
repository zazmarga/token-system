from fastapi import FastAPI
from app.routers.admin import admin_router
from app.routers.internal import internal_router
from app.routers.public import public_router

from app.core.logging_config import setup_logging

setup_logging()


app = FastAPI(
    title="Token System",
    description="Сервіс для керування токенами, кредитами та підписками",
    version="1.0.0"
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(internal_router)
app.include_router(public_router)
app.include_router(admin_router)
