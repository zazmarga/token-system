from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import access_admin, get_db
from app.models.settings import Settings
from app.models.subscription import SubscriptionPlan
from app.schemas.admin import ExchangeRateResponse, ExchangeRateUpdate
from app.schemas.subscription import (
    SubscriptionPlanResponse,
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate
)

# Admin API
admin_router = APIRouter(prefix="/api/admin", tags=["Admin API"])


@admin_router.patch(
    "/settings/exchange-rate",
    dependencies=[Depends(access_admin)],
    summary="Оновлення базового курсу конвертації",
    description="Доступ лише для адміністратора. Headers: X-Admin-Token",
    response_model=ExchangeRateResponse,
    status_code=status.HTTP_200_OK,
    responses={
        403: {
            "description": "Forbidden.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid admin token."}
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
async def update_exchange_rate(
        payload: ExchangeRateUpdate,
        db: AsyncSession = Depends(get_db)
):
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


@admin_router.post(
    "/subscription-plans",
    dependencies=[Depends(access_admin)],
    summary="Створення тарифного плану",
    description="Доступ лише для адміністратора. Headers: X-Admin-Token",
    response_model=SubscriptionPlanResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {
            "description": "Forbidden.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid admin token."}
                },
            },
        },
        409: {
            "description": "Conflict.",
            "content": {
                "application/json": {
                    "example": {"detail": "Unique: tier/name already exists."}
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
async def create_subscription_plan(
        payload: SubscriptionPlanCreate,
        db: AsyncSession = Depends(get_db)
):
    plan_by_tier = await db.get(SubscriptionPlan, payload.tier)
    if plan_by_tier:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Unique: tier='{payload.tier}' already exists."
        )

    result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.name == payload.name))
    plan_by_name = result.scalar_one_or_none()
    if plan_by_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Unique: name='{payload.name}' already exists."
        )

    new_plan = SubscriptionPlan(
        **payload.model_dump(exclude_unset=True, exclude_none=True)
    )
    db.add(new_plan)
    await db.commit()
    await db.refresh(new_plan)
    return SubscriptionPlanResponse(success=True, plan=new_plan)


@admin_router.put(
    "/subscription-plans/{tier}",
    dependencies=[Depends(access_admin)],
    summary="Оновлення тарифного плану",
    description="Доступ лише для адміністратора. Headers: X-Admin-Token",
    response_model=SubscriptionPlanResponse,
    status_code=status.HTTP_200_OK,
    responses={
        403: {
            "description": "Forbidden.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid admin token."}
                },
            },
        },
        404: {
            "description": "Not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Plan not found."}
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
async def create_subscription_plan(
        tier: str,
        payload: SubscriptionPlanUpdate,
        db: AsyncSession = Depends(get_db)
):
    plan = await db.get(SubscriptionPlan, tier)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan '{tier}' not found")

    for k, v in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(plan, k, v)
        await db.commit()
        await db.refresh(plan)
    return SubscriptionPlanResponse(success=True, plan=plan)
