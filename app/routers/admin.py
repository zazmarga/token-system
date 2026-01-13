from datetime import date, datetime, timezone, time
from typing import Optional

from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import access_admin, get_session
from app.models import Credits, Transaction, TransactionType
from app.models.user import User
from app.models.settings import AdminLog, AdminOperationType
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

import logging

from app.utils.common import dump_payload, tier_existing_check, get_base_rate_from_settings
from app.utils.logging import generate_admin_log_id, get_extra_data_log

logger = logging.getLogger("[ADMIN]")


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
        session: AsyncSession = Depends(get_session)
):
    # завантаження базового курсу конвертації
    base_rate, created, settings = await get_base_rate_from_settings(session)

    if created:
        result = {
            "success": True,
            "old_base_rate": 0,
            "new_base_rate": payload.base_rate,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        message = "Created base rate. AdminLog:"
    else:
        old_rate = base_rate
        settings.base_rate = payload.base_rate

        result = {
            "success": True,
            "old_base_rate": old_rate,
            "new_base_rate": settings.base_rate,
            "updated_at": settings.updated_at.isoformat()
        }
        message = "Changed base rate. AdminLog:"
    # create new AdminLog
    operation_type = AdminOperationType.UPDATE_BASE_RATE.value
    new_admin_log = AdminLog(
        id=generate_admin_log_id(operation_type),
        operation_type=operation_type.upper(),
        entity="Settings",
        entity_id=str(settings.id),
        changes=result
    )

    session.add(new_admin_log)
    await session.flush()

    logger.info(
        message, extra=get_extra_data_log(new_admin_log)
    )
    await session.commit()
    return result


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
        session: AsyncSession = Depends(get_session)
):
    plan_by_tier = await session.get(SubscriptionPlan, payload.tier)
    if plan_by_tier:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Unique: tier='{payload.tier}' already exists."
        )

    result = await (session
                    .execute(select(SubscriptionPlan)
                    .where(SubscriptionPlan.name == payload.name)))
    plan_by_name = result.scalar_one_or_none()
    if plan_by_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Unique: tier='{payload.name}' already exists."
        )

    new_plan = SubscriptionPlan(**dump_payload(payload))

    session.add(new_plan)
    await session.flush()

    # create new AdminLog
    operation_type = AdminOperationType.CREATE_PLAN.value
    new_admin_log = AdminLog(
        id=generate_admin_log_id(operation_type),
        operation_type=operation_type.upper(),
        entity="SubscriptionPlan",
        entity_id=payload.tier,
        changes={"success": True, **dump_payload(payload)}
    )

    session.add(new_admin_log)
    await session.flush()

    logger.info(
        "Created new subscription plan. AdminLog:",
        extra=get_extra_data_log(new_admin_log)
    )

    await session.commit()
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
        session: AsyncSession = Depends(get_session)
):

    # перевірка tier існує? як що ні: Exception
    await tier_existing_check(session, tier)

    plan: SubscriptionPlan = await session.get(SubscriptionPlan, tier)

    for k, v in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(plan, k, v)
    await session.flush()
    await session.refresh(plan)

    # create new AdminLog
    operation_type = AdminOperationType.UPDATE_PLAN.value
    new_admin_log = AdminLog(
        id=generate_admin_log_id(operation_type),
        operation_type=operation_type.upper(),
        entity="SubscriptionPlan",
        entity_id=plan.tier,
        changes={"success": True, **dump_payload(payload)}
    )

    session.add(new_admin_log)
    await session.flush()

    logger.info(
        "Updated subscription plan. AdminLog:", extra=get_extra_data_log(new_admin_log)
    )
    await session.commit()
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
        session: AsyncSession = Depends(get_session)
):
    # перевірка tier існує? як що ні: Exception
    await tier_existing_check(session, tier)

    plan = await session.get(SubscriptionPlan, tier)
    await session.delete(plan)
    await session.flush()

    # create new AdminLog
    operation_type = AdminOperationType.DELETE_PLAN.value
    new_admin_log = AdminLog(
        id=generate_admin_log_id(operation_type),
        operation_type=operation_type.upper(),
        entity="SubscriptionPlan",
        entity_id=tier,
        changes={"success": True}
    )

    session.add(new_admin_log)
    await session.flush()

    logger.info(
        "Deleted subscription plan. AdminLog:",
        extra=get_extra_data_log(new_admin_log)
    )

    await session.commit()
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
    session: AsyncSession = Depends(get_session)
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

    result = await session.execute(query)
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
        session: AsyncSession = Depends(get_session)
):
    # перевірка tier існує? як що ні: Exception
    await tier_existing_check(session, tier)

    plan = await session.get(SubscriptionPlan, tier)

    old_multiplier = plan.multiplier
    plan.multiplier = multiplier

    # create new AdminLog
    operation_type = AdminOperationType.UPDATE_MULTIPLIER.value
    new_admin_log = AdminLog(
        id=generate_admin_log_id(operation_type),
        operation_type=operation_type.upper(),
        entity="SubscriptionPlan.multiplier",
        entity_id=tier,
        changes={
            "success": True,
            "tier": tier,
            "multiplier": float(old_multiplier),
            "new_multiplier": multiplier
        }
    )

    session.add(new_admin_log)
    await session.flush()
    logger.info(
        "Updated multiplier. AdminLog:",
        extra=get_extra_data_log(new_admin_log)
    )

    await session.commit()
    await session.refresh(plan)

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
        session: AsyncSession = Depends(get_session)
):
    # перевірка tier існує? як що ні: Exception
    await tier_existing_check(session, tier)

    plan = await session.get(SubscriptionPlan, tier)

    old_purchase_rate = plan.purchase_rate
    plan.purchase_rate = purchase_rate

    # create new AdminLog
    operation_type = AdminOperationType.UPDATE_PURCHASE_RATE.value
    new_admin_log = AdminLog(
        id=generate_admin_log_id(operation_type),
        operation_type=operation_type.upper(),
        entity="SubscriptionPlan.purchase_rate",
        entity_id=tier,
        changes={
            "success": True,
            "tier": tier,
            "old_purchase_rate": float(old_purchase_rate),
            "new_purchase_rate": purchase_rate
        }
    )

    session.add(new_admin_log)
    await session.flush()

    logger.info(
        "Updated purchase rate. AdminLog:",
        extra=get_extra_data_log(new_admin_log)
    )

    await session.commit()
    await session.refresh(plan)

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
    start_date: date = Query(..., description="Start date (e.g. 2026-01-01)"),
    end_date: date = Query(..., description="End date (e.g. 2026-01-31)"),
    tier: Optional[str] = Query(None, description="Tier: optional"),
    session: AsyncSession = Depends(get_session)
):
    if tier:
        # перевірка tier існує? як що ні: Exception
        await tier_existing_check(session, tier)

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

    result = await session.execute(stmt)
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

    result = await session.execute(stmt)
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
        .where(Transaction.created_at >= start)
        .where(Transaction.created_at <= end)
    )

    if tier:
        stmt = stmt.where(SubscriptionPlan.tier == tier)

    result = await session.execute(stmt)
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
