from fastapi import APIRouter


# Internal API (для інших внутрішніх сервісів)
internal_router = APIRouter(prefix="/api/internal", tags=["Internal API"])


@internal_router.get("/health-internal")
def health_internal():
    return {"status": "ok"}
