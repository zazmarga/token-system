from datetime import date, datetime, timezone, time
from typing import Optional

from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import access_admin, get_db
from app.models import Credits, Transaction, TransactionType
from app.models.user import User
from app.models.settings import Settings
from app.models.subscription import SubscriptionPlan, Subscription
from app.schemas.admin import ExchangeRateResponse, ExchangeRateUpdate
from app.schemas.base import (
    StatisticsResponse, StatisticsPeriod, StatisticsPlans,
    StatisticsCredits, StatisticsTransactions
)
from app.schemas.subscription import (
    SubscriptionPlanResponse,
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    SubscriptionPlanList,
    SubscriptionPlanDetail,
    MultiplierUpdateResponse,
    PurchaseRateUpdateResponse,
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
async def update_subscription_plan(
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


@admin_router.delete(
    "/subscription-plans/{tier}",
    dependencies=[Depends(access_admin)],
    summary="Видалення тарифного плану",
    description="Доступ лише для адміністратора. Headers: X-Admin-Token",
    status_code=status.HTTP_200_OK,
    response_model=dict,
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
async def delete_subscription_plan(
        tier: str,
        db: AsyncSession = Depends(get_db)
):
    plan = await db.get(SubscriptionPlan, tier)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan '{tier}' not found")
    await db.delete(plan)
    await db.commit()
    return {
        "success": True,
        "message": "Subscription plan deleted",
        "tier": tier
    }


@admin_router.get(
    "/subscription-plans",
    dependencies=[Depends(access_admin)],
    summary="Отримання списку тарифних планів з кількістю користувачів",
    description="Доступ лише для адміністратора. Headers: X-Admin-Token",
    response_model=SubscriptionPlanList,
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
async def list_subscription_plans(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(
            SubscriptionPlan,
            func.count(User.id).label("users_count")
        )
        .outerjoin(Subscription,Subscription.plan_id == SubscriptionPlan.tier)
        .outerjoin(User, User.id == Subscription.user_id)
        .group_by(SubscriptionPlan.tier)
    )

    if active_only:
        query = query.where(SubscriptionPlan.active.is_(True))

    result = await db.execute(query)
    rows = result.all()

    plans_with_counts = [
        SubscriptionPlanDetail(
            **row.SubscriptionPlan.__dict__,
            users_count=row.users_count
        )
        for row in rows
    ]

    return SubscriptionPlanList(plans=plans_with_counts)


@admin_router.patch(
    "/subscription-plans/{tier}/multiplier",
    dependencies=[Depends(access_admin)],
    summary="Оновлення коефіцієнту списання для тарифного плану",
    description="Доступ лише для адміністратора. Headers: X-Admin-Token",
    response_model=MultiplierUpdateResponse,
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
async def update_multiplier(
        tier: str,
        multiplier: float,
        db: AsyncSession = Depends(get_db)
):
    plan = await db.get(SubscriptionPlan, tier)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan '{tier}' not found")

    old_multiplier = plan.multiplier
    plan.multiplier = multiplier
    await db.commit()
    await db.refresh(plan)

    return MultiplierUpdateResponse(
        success=True,
        tier=tier,
        old_multiplier=old_multiplier,
        new_multiplier=multiplier,
        updated_at=plan.updated_at
    )


@admin_router.patch(
    "/subscription-plans/{tier}/purchase-rate",
    dependencies=[Depends(access_admin)],
    summary="Оновлення ставки покупки кредитів для тарифного плану",
    description="Доступ лише для адміністратора. Headers: X-Admin-Token",
    response_model=PurchaseRateUpdateResponse,
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
async def update_purchase_rate(
        tier: str,
        purchase_rate: float,
        db: AsyncSession = Depends(get_db)
):
    plan = await db.get(SubscriptionPlan, tier)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan '{tier}' not found")

    old_purchase_rate = plan.purchase_rate
    plan.purchase_rate = purchase_rate
    await db.commit()
    await db.refresh(plan)

    return PurchaseRateUpdateResponse(
        success=True,
        tier=tier,
        old_purchase_rate=old_purchase_rate,
        new_purchase_rate=purchase_rate,
        updated_at=plan.updated_at
    )


@admin_router.get(
    "/statistics",
    dependencies=[Depends(access_admin)],
    summary="Отримання статистики використання",
    description="Доступ лише для адміністратора. Headers: X-Admin-Token",
    response_model=StatisticsResponse,
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
async def get_usage_statistics(
    start_date: date = Query(..., description="Start date (ISO 8601, e.g. 2026-01-01)"),
    end_date: date = Query(..., description="End date (ISO 8601, e.g. 2026-01-31)"),
    tier: Optional[str] = Query(None, description="Tier: optional"),
    db: AsyncSession = Depends(get_db)
):
    # формування дати-часу з дати
    start: datetime = datetime.combine(start_date, time(0, 0, 0), tzinfo=timezone.utc)
    end: datetime = datetime.combine(end_date, time(23, 59, 59), tzinfo=timezone.utc)

    # dict з кількістю users у кожний підписці
    # загальна кількість користувачів які мають підписку
    stmt = (
        select(SubscriptionPlan.tier, func.count(User.id))
        .join(Subscription, Subscription.user_id == User.id)
        .join(SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.tier)
        .group_by(SubscriptionPlan.tier)
    )

    result = await db.execute(stmt)
    rows = result.all()

    subscriptions = {tier: count for tier, count in rows}
    total_users = sum(subscriptions.values())
    if tier:
        if tier in subscriptions:
            subscriptions = {tier: subscriptions[tier]}
            total_users = subscriptions[tier]
        else:
            subscriptions = {}
            total_users = 0

    # статистика по кредитам
    stmt = (
        select(
            func.sum(Credits.total_earned).label("total_earned"),
            func.sum(Credits.total_spent).label("total_spent"),
        )
        .select_from(User)
        .join(Subscription, Subscription.user_id == User.id)
        .join(SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.tier)
    )

    if tier:
        stmt = stmt.where(SubscriptionPlan.tier == tier)

    result = await db.execute(stmt)
    row = result.one()

    total_earned = row.total_earned or 0
    total_spent = row.total_spent or 0
    current_balance = total_earned - total_spent

    # статистика кількості транзакцій
    stmt = (
        select(
            func.count(Transaction.id).label("total"),
            func.sum(case((Transaction.type == TransactionType.CHARGE, 1), else_=0)).label("charges"),
            func.sum(case((Transaction.type == TransactionType.ADD, 1), else_=0)).label("additions"),
        )
        .join(Subscription, Subscription.user_id == Transaction.user_id)
        .join(SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.tier)
        .where(Transaction.created_at >= start_date)
        .where(Transaction.created_at < end_date)
    )

    if tier:
        stmt = stmt.where(SubscriptionPlan.tier == tier)

    result = await db.execute(stmt)
    row = result.one()

    total = row.total or 0
    charges = row.charges or 0
    additions = row.additions or 0

    return StatisticsResponse(
        period=StatisticsPeriod(
            start=start,
            end=end
        ),
        total_users=total_users,
        subscriptions=StatisticsPlans(subscriptions=subscriptions),
        credits=StatisticsCredits(
            total_earned=total_earned,
            total_spent=total_spent,
            current_balance=current_balance
        ),
        transactions=StatisticsTransactions(
            total=total,
            charges=charges,
            additions=additions
        )
    )
