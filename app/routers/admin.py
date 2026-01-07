from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import access_admin, get_db
from app.models.settings import Settings
from app.schemas.admin import ExchangeRateResponse, ExchangeRateUpdate

# Admin API
admin_router = APIRouter(prefix="/api/admin", tags=["Admin API"])


@admin_router.patch(
    "/settings/exchange-rate",
    summary="Оновлення базового курсу конвертації",
    description="Доступ лише для адміністратора. Headers: X-Admin-Token",
    response_model=ExchangeRateResponse,
    dependencies=[Depends(access_admin)],
    status_code=status.HTTP_200_OK,
    responses={
        403: {
            "description": "Forbidden.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid admin token"}
                },
            },
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {"detail": "Internal Server Error."}
                }
            },
        },
    },
)
async def update_exchange_rate(payload: ExchangeRateUpdate, db: AsyncSession = Depends(get_db)):
    settings = await db.execute(select(Settings))
    settings = settings.scalars().first()
    if not settings:
        # створюємо новий запис
        new_settings = Settings(base_rate=payload.base_rate)
        db.add(new_settings)
        await db.commit()
        await db.refresh(new_settings)
        return {
            "success": True,
            "old_base_rate": payload.base_rate,
            "new_base_rate": payload.base_rate,
            "updated_at": new_settings.updated_at.isoformat()
        }

    old_rate = settings.base_rate
    settings.base_rate = payload.base_rate
    await db.commit()
    await db.refresh(settings)

    return {
        "success": True,
        "old_base_rate": old_rate,
        "new_base_rate": settings.base_rate,
        "updated_at": settings.updated_at.isoformat()
    }
