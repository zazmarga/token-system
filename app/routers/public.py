from fastapi import APIRouter, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.models.subscription import SubscriptionPlan
from app.schemas.subscription import SubscriptionPlanPublicList

# API для фронтенду (зовнішні користувачі)
public_router = APIRouter(prefix="/api/v1", tags=["Public API"])


@public_router.get(
    "/subscription/plans",
    summary="Отримання доступних тарифних планів",
    response_model=SubscriptionPlanPublicList,
    status_code=status.HTTP_200_OK,
    responses={
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
async def list_available_subscription_plans(
    db: AsyncSession = Depends(get_db)
):
    query = select(SubscriptionPlan).where(SubscriptionPlan.active.is_(True))

    result = await db.execute(query)
    plans = result.scalars().all()

    return SubscriptionPlanPublicList(plans=plans)

