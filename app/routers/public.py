from fastapi import APIRouter


# API для фронтенду (зовнішні користувачі)
public_router = APIRouter(prefix="/api/v1", tags=["Public API"])


@public_router.get("/health-public")
def health_public():
    return {"status": "ok"}
