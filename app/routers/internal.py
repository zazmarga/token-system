from datetime import datetime, timezone
from logging import info
from typing import Optional

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import access_internal, get_db
from app.utils.idempotency import check_idempotency
from app.models import (
    Subscription, User, Transaction, Credits, TransactionType,
    TransactionSource, SubscriptionPlan, Settings
)
from app.schemas.credits import (
    CreditsUserBalanceResponse, CreditsBase, CreditsUserCheckResponse,
    CreditsAddResponse, CreditsAddRequest
)
from app.schemas.subscription import (
    SubscriptionUpdateResponse, SubscriptionUpdateRequest,
    SubscriptionPlanInternal)

# Internal API (для інших внутрішніх сервісів)
internal_router = APIRouter(prefix="/api/internal", tags=["Internal API"])


@internal_router.post(
    "/subscription/update",
    dependencies=[Depends(access_internal)],
    summary="Оновлення підписки користувача",
    description="Лише внутрішний доступ. Headers: X-Service-Token",
    response_model=SubscriptionUpdateResponse,
    status_code=status.HTTP_200_OK,
    responses={
        403: {
            "description": "Forbidden.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid service token."}
                },
            },
        },
        404: {
            "description": "Not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "User not found."}
                },
            },
        },
        409: {
            "description": "Conflict.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Operation ID already used for different operation type"
                    }
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
    payload: SubscriptionUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    user_id = payload.user_id

    # перевірка user
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )

    # Перевіряємо ідемпотентність
    is_duplicate, existing_tx = await check_idempotency(
        db=db,
        operation_id=payload.operation_id,
        expected_type=TransactionType.SUBSCRIPTION.value
    )

    if is_duplicate and existing_tx is not None:
        metadata = existing_tx.info
        # Повертаємо той самий результат, що був раніше
        return SubscriptionUpdateResponse(
            success=True,
            user_id=existing_tx.user_id,
            previous_tier=metadata.get("previous_tier"),
            new_tier=metadata.get("new_tier"),
            credits_added=existing_tx.credits,
            new_balance=existing_tx.balance_after,
            multiplier=metadata.get("multiplier"),
            purchase_rate=metadata.get("purchase_rate"),
        )

    # завантажуємо підписку разом із планом
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.user_id == user_id)
    )
    user_subscription: Subscription | None = result.scalar_one_or_none()

    # атомарна транзакція
    async with db.begin_nested():
        if not user_subscription:
            previous_tier = None
            user_subscription = Subscription(user_id=user_id, plan_id=payload.subscription_tier)
            db.add(user_subscription)
            plan = await db.get(SubscriptionPlan, payload.subscription_tier)
        else:
            previous_tier = user_subscription.plan.tier
            user_subscription.plan_id = payload.subscription_tier
            plan = user_subscription.plan

        # кредити
        result = await db.execute(select(Credits).where(Credits.user_id == user_id))
        user_credit = result.scalar_one_or_none()
        if not user_credit:
            user_credit = Credits(user_id=user_id, balance=0, total_earned=0)
            db.add(user_credit)

        balance_before = user_credit.balance
        user_credit.balance += payload.credits_to_add
        user_credit.total_earned += payload.credits_to_add
        balance_after = user_credit.balance
        new_tier = payload.subscription_tier
        multiplier = plan.multiplier
        purchase_rate = plan.purchase_rate
        credits_to_add = payload.credits_to_add
        operation_id = payload.operation_id
        tx_id = f"txn_{operation_id[3:]}"

        # транзакція
        new_tx = Transaction(
            id=tx_id,
            user_id=user_id,
            operation_id=operation_id,
            type=TransactionType.SUBSCRIPTION,
            source=TransactionSource.SUBSCRIPTION,
            credits=credits_to_add,
            balance_before=balance_before,
            balance_after=balance_after,
            description=f"Subscription update to {new_tier}",
            created_at=datetime.now(timezone.utc),
            info={
                "previous_tier": previous_tier,
                "new_tier": new_tier,
                "multiplier": float(multiplier),
                "purchase_rate": float(purchase_rate),
            }
        )
        db.add(new_tx)
        await db.commit()

    return SubscriptionUpdateResponse(
        success=True,
        user_id=user_id,
        previous_tier=previous_tier,
        new_tier=new_tier,
        credits_added=credits_to_add,
        new_balance=balance_after,
        multiplier=multiplier,
        purchase_rate=purchase_rate
    )


@internal_router.get(
    "/credits/balance/{user_id}",
    dependencies=[Depends(access_internal)],
    summary="Отримання балансу користувача",
    description="Лише внутрішний доступ. Headers: X-Service-Token",
    response_model=CreditsUserBalanceResponse,
    status_code=status.HTTP_200_OK,
    responses={
        403: {
            "description": "Forbidden.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid service token."}
                },
            },
        },
        404: {
            "description": "Not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "User not found."}
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
async def user_credits_balance(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )

    # завантажуємо підписку разом із планом
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        return CreditsUserBalanceResponse(
            user_id=user_id,
            subscription=SubscriptionPlanInternal(
                tier=None,
                monthly_cost=0,
                multiplier=1,
                purchase_rate=1
            ),
            credits=CreditsBase(
                balance=0,
                total_earned=0,
                total_spent=0
            )
        )
    plan = subscription.plan

    # кредити
    result = await db.execute(select(Credits).where(Credits.user_id == user_id))
    user_credits = result.scalar_one_or_none()

    return CreditsUserBalanceResponse(
        user_id=user_id,
        subscription=SubscriptionPlanInternal(
            tier=plan.tier,
            monthly_cost=plan.monthly_cost,
            multiplier=plan.multiplier,
            purchase_rate=plan.purchase_rate
        ),
        credits=CreditsBase(
            balance=user_credits.balance,
            total_earned=user_credits.total_earned,
            total_spent=user_credits.total_spent
        )
    )


@internal_router.get(
    "/credits/check/{user_id}",
    dependencies=[Depends(access_internal)],
    summary="Перевірка наявності кредитів",
    description="Лише внутрішній доступ. Headers: X-Service-Token",
    response_model=CreditsUserCheckResponse,
    status_code=status.HTTP_200_OK,
    responses={
        403: {
            "description": "Forbidden.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid service token."}
                },
            },
        },
        404: {
            "description": "Not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "User not found."}
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
async def user_credits_checking(
    user_id: str,
    required_credits: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )

    # завантажуємо підписку разом із планом
    result = await db.execute(
        select(
            Subscription,
            SubscriptionPlan.tier,
            SubscriptionPlan.multiplier
        )
        .outerjoin(SubscriptionPlan,
                   Subscription.plan_id == SubscriptionPlan.tier)
        .where(Subscription.user_id == user_id)
    )
    row = result.first()
    if not row:
        return CreditsUserCheckResponse(
            user_id=user_id,
            has_subscription=False,
            subscription_tier=None,
            balance=0,
            sufficient=False,
            multiplier=1
        )

    subscription, tier, multiplier = row

    # кредити
    balance_result = await db.execute(
        select(Credits.balance).where(Credits.user_id == user_id)
    )
    balance: int = balance_result.scalar_one_or_none() or 0

    if required_credits is None:
        sufficient = True
    else:
        sufficient = balance >= required_credits

    return CreditsUserCheckResponse(
        user_id=user_id,
        has_subscription=True,
        subscription_tier=tier,
        balance=balance,
        sufficient=sufficient,
        multiplier=multiplier,
    )


@internal_router.post(
    "/credits/add",
    dependencies=[Depends(access_internal)],
    summary="Додавання кредитів: поповнення балансу",
    description="Лише внутрішній доступ. Headers: X-Service-Token",
    response_model=CreditsAddResponse,
    status_code=status.HTTP_200_OK,
    responses={
        403: {
            "description": "Forbidden.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid service token."}
                },
            },
        },
        404: {
            "description": "Not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "User not found."}
                },
            },
        },
        409: {
            "description": "Conflict.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Operation ID already used for different operation type"
                    }
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
async def user_credits_add(
        payload: CreditsAddRequest,
        db: AsyncSession = Depends(get_db)
):
    user_id = payload.user_id
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )

    # Перевіряємо ідемпотентність
    operation_id = payload.operation_id
    is_duplicate, existing_tx = await check_idempotency(
        db=db,
        operation_id=operation_id,
        expected_type=TransactionType.ADD.value
    )

    if is_duplicate and existing_tx is not None:
        metadata = existing_tx.info
        # Повертаємо той самий результат, що був раніше
        return CreditsAddResponse(
            success=True,
            transaction_id=existing_tx.id,
            user_id=existing_tx.user_id,
            amount_usd=existing_tx.amount_usd,
            credits_added=existing_tx.credits,
            purchase_rate=metadata.get("purchase_rate"),
            balance_before=existing_tx.balance_before,
            balance_after=existing_tx.balance_after,
            operation_id=existing_tx.operation_id
        )

    # завантажуємо підписку разом із планом
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.user_id == user_id)
    )
    subscription: Subscription | None = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Not found: user '{user_id}' does not have subscription.",
        )
    purchase_rate = float(subscription.plan.purchase_rate)

    # завантаження базового курсу конвертації
    settings = await db.execute(select(Settings))
    settings = settings.scalars().first()
    if not settings:
        settings = Settings()
        db.add(settings)
        await db.commit()
    base_rate = settings.base_rate

    # розрахунок суми кредитів з урахуванням бонусу підписки
    amount_usd = payload.amount_usd
    credits_added = round(amount_usd * purchase_rate * base_rate)

    # кредити
    result = await db.execute(select(Credits).where(Credits.user_id == user_id))
    user_credits: Credits | None = result.scalar_one_or_none()
    if not user_credits:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Not found: user '{user_id}' does not have subscription.",
        )

    # оновити кредити та створити транзакцію
    async with db.begin_nested():
        # оновити кредити
        user_credits.total_earned += credits_added
        balance_before = user_credits.balance
        user_credits.balance += credits_added
        balance_after = balance_before + credits_added
        id_tx = f"txn_{operation_id[3:]}"

        meta = payload.metadata
        if hasattr(meta, "dict"):
            meta = meta.dict()
        info = {"purchase_rate": float(purchase_rate)} | meta

        # транзакція
        new_tx = Transaction(
            id=id_tx,
            user_id=user_id,
            operation_id=operation_id,
            type=TransactionType.ADD,
            source=TransactionSource.PURCHASE,
            credits=credits_added,
            balance_before=balance_before,
            balance_after=balance_after,
            description=payload.description,
            created_at=datetime.now(timezone.utc),
            info=info
        )
        db.add(new_tx)
        await db.commit()

    return CreditsAddResponse(
        success=True,
        transaction_id=new_tx.id,
        user_id=user_id,
        amount_usd=amount_usd,
        credits_added=credits_added,
        purchase_rate=purchase_rate,
        balance_before=balance_before,
        balance_after=balance_after,
        operation_id=operation_id
    )
