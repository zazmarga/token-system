from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import access_internal, get_db
from app.models import Subscription, User, Transaction, Credits, TransactionType, TransactionSource
from app.schemas.subscription import SubscriptionUpdateResponse, SubscriptionUpdateRequest

# Internal API (для інших внутрішніх сервісів)
internal_router = APIRouter(prefix="/api/internal", tags=["Internal API"])


@internal_router.post(
    "/subscription/update",
    dependencies=[Depends(access_internal)],
    summary="Оновлення підписки користувача",
    description="Доступний лише внутрішний доступ. Headers: X-Service-Token",
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
                    "example": {"detail": "Transaction already exists."}
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

    # атомарна транзакція
    async with db.begin():
        # перевірка user
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
        user_subscription = result.scalar_one_or_none()

        if not user_subscription:
            previous_tier = None
            user_subscription = Subscription(user_id=user_id, plan_id=payload.subscription_tier)
            db.add(user_subscription)
        else:
            previous_tier = user_subscription.plan.tier
            user_subscription.plan_id = payload.subscription_tier

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

        # перевірка на дублікат operation_id
        existing_tx = await db.execute(
            select(Transaction).where(Transaction.operation_id == payload.operation_id)
        )
        if existing_tx.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Transaction with operation_id '{payload.operation_id}' already exists."
            )

        # транзакція
        new_tx = Transaction(
            user_id=user_id,
            operation_id=payload.operation_id,
            type=TransactionType.SUBSCRIPTION,
            source=TransactionSource.SUBSCRIPTION,
            credits=payload.credits_to_add,
            balance_before=balance_before,
            balance_after=balance_after,
            description=f"Subscription update to {payload.subscription_tier}",
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_tx)

    await db.refresh(user_subscription)
    await db.refresh(user_credit)
    await db.refresh(new_tx)

    return SubscriptionUpdateResponse(
        success=True,
        user_id=user_id,
        previous_tier=previous_tier,
        new_tier=payload.subscription_tier,
        credits_added=payload.credits_to_add,
        new_balance=user_credit.balance,
        multiplier=user_subscription.plan.multiplier,
        purchase_rate=user_subscription.plan.purchase_rate
    )
