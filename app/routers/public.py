from typing import Optional, List

from fastapi import APIRouter, status, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_session, get_current_user
from app.models import TransactionSource, Credits, TransactionType, Transaction
from app.models.subscription import SubscriptionPlan, Subscription
from app.schemas.base import UserCreditsBase
from app.schemas.credits import CreditsPurchaseResponse, CreditsPurchasePayload
from app.schemas.serializers import serialize_transaction
from app.schemas.subscription import (
    SubscriptionPlanPublicList, UserSubscriptionResponse,
    SubscriptionPlanPublicDetail
)
from app.schemas.transactions import TransactionPublicPaginatedList
from app.utils.common import generate_operation_id, is_payment_complete
from app.utils.http_client import call_internal_api


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
    session: AsyncSession = Depends(get_session)
):
    query = select(SubscriptionPlan).where(SubscriptionPlan.active.is_(True))

    result = await session.execute(query)
    plans = result.scalars().all()

    return SubscriptionPlanPublicList(plans=plans)


@public_router.post(
    "/credits/purchase",
    summary="Поповнення кредитів",
    description="Доступ для user з token. Headers: Authorization: Bearer {user_token}",
    response_model=CreditsPurchaseResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "description": "Unauthorized.",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated."}
                },
            },
        },
        403: {
            "description": "Forbidden.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid user token."}
                },
            },
        },
        402: {
            "description": "Payment required.",
            "content": {
                "application/json": {
                    "example": {"detail": "Payment not completed."}
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
async def credits_purchase_by_user(
        payload: CreditsPurchasePayload,
        user_id: str = Depends(get_current_user),
        session: AsyncSession = Depends(get_session)

):
    source = TransactionSource.PURCHASE.value

    if not is_payment_complete(payload.payment_method_id):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Payment '{payload.payment_method_id}' not completed."
        )

    operation_id = await generate_operation_id(session, source=source)

    internal_payload = {
        "user_id": user_id,
        "amount_usd": payload.amount_usd,
        "source": source,
        "operation_id": operation_id,
        "description": "Credit purchase",
        "metadata": {"payment_method_id": payload.payment_method_id}
    }

    internal_result = await call_internal_api(
        "/api/internal/credits/add", internal_payload)

    return CreditsPurchaseResponse(
        success=True,
        transaction_id=internal_result["transaction_id"],
        amount_usd=payload.amount_usd,
        credits_added=internal_result["credits_added"],
        new_balance=internal_result["balance_after"]
    )


@public_router.get(
    "/subscription",
    summary="Отримання інформації про підписку користувача",
    description="Доступ для user з token. Headers: Authorization: Bearer {user_token}",
    response_model=UserSubscriptionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "description": "Unauthorized.",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated."}
                },
            },
        },
        403: {
            "description": "Forbidden.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid user token."}
                },
            },
        },
        404: {
            "description": "Not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Subscription not found."}
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
async def user_subscription(
        user_id: str = Depends(get_current_user),
        session: AsyncSession = Depends(get_session)
):
    # підписка та план підписки
    result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.user_id == user_id)
    )
    subscription: Subscription | None = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription of user '{user_id}' not found."
        )

    plan = subscription.plan

    # кредити
    result = await session.execute(
        select(Credits)
        .where(Credits.user_id == user_id)
    )
    user_credits: Credits | None = result.scalar_one_or_none()

    return UserSubscriptionResponse(
        subscription=SubscriptionPlanPublicDetail(
            tier=plan.tier,
            name=plan.name,
            monthly_cost=plan.monthly_cost,
            fixed_cost=plan.fixed_cost,
            credits_included=plan.credits_included,
            bonus_credits=plan.bonus_credits,
            multiplier=plan.multiplier,
            purchase_rate=plan.purchase_rate
        ),
        credits=UserCreditsBase(
            balance=user_credits.balance,
            total_earned=user_credits.total_earned,
            total_spent=user_credits.total_spent
        )
    )


@public_router.get(
    "/transactions",
    summary="Історія транзакцій",
    response_model=TransactionPublicPaginatedList,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "description": "Unauthorized.",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated."}
                },
            },
        },
        403: {
            "description": "Forbidden.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid user token."}
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
async def list_user_transactions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    type: Optional[TransactionType] = Query(None),
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # базовий запит
    stmt = select(Transaction).where(Transaction.user_id == user_id)

    # фільтр по типу
    if type:
        stmt = stmt.where(Transaction.type == type.value.upper())

    # підрахунок total
    count_stmt = select(func.count()).select_from(Transaction).where(Transaction.user_id == user_id)
    if type:
        count_stmt = count_stmt.where(Transaction.type == type.value.upper())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    # пагінація
    stmt = stmt.order_by(Transaction.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    db_transactions: List[Transaction] = result.scalars().all()

    transactions = [serialize_transaction(t) for t in db_transactions]

    return TransactionPublicPaginatedList(
        total=total,
        limit=limit,
        offset=offset,
        transactions=transactions
    )
