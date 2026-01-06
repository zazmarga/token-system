from fastapi import APIRouter


# Admin API
admin_router = APIRouter(prefix="/api/admin", tags=["Admin API"])


@admin_router.get("/health-admin")
def health_admin():
    return {"status": "ok"}
