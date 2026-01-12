from datetime import datetime, timezone
from typing import Optional, Union

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import (
    get_session, access_internal, get_balance_service
)
from app.utils.common import (
    generate_transaction_id, user_existing_check,
    calculate_credits_amount, get_base_rate_from_settings
)
from app.utils.idempotency import check_idempotency
from app.models import (
    Subscription, Transaction, TransactionType,
    TransactionSource, SubscriptionPlan, Settings
)
from app.schemas.credits import (
    CreditsUserBalanceResponse, CreditsBase, CreditsUserCheckResponse,
    CreditsAddResponse, CreditsAddRequest, CreditsCalculateResponse,
    CreditsCalculateRequest, CreditsChargeRequest, CreditsChargeSuccessResponse,
    CreditsChargeNoSuccessResponse
)
from app.schemas.subscription import (
    SubscriptionUpdateResponse, SubscriptionUpdateRequest,
    SubscriptionPlanInternal)
from app.utils.logging import get_extra_data_log
from app.utils.service_balance import BalanceService

import logging
logger = logging.getLogger("[INTERNAL]")


# Internal API (для інших внутрішніх сервісів)
internal_router = APIRouter(prefix="/api/internal", tags=["Internal API"])


@internal_router.post(
    "/subscription/update",
    dependencies=[Depends(access_internal)],
    summary="Оновлення підписки користувача",
    description="Лише внутрішній доступ. Headers: X-Service-Token",
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
async def create_user_subscription_plan(
    payload: SubscriptionUpdateRequest,
    session: AsyncSession = Depends(get_session),
    balance_service: BalanceService = Depends(get_balance_service)
):
    user_id = payload.user_id

    # перевірка user існує? як що ні: Exception
    await user_existing_check(session, user_id)

    # Перевіряємо ідемпотентність
    is_duplicate, existing_tx = await check_idempotency(
        session=session,
        operation_id=payload.operation_id,
        expected_type=TransactionType.SUBSCRIPTION.value
    )

    if is_duplicate and existing_tx is not None:
        metadata = existing_tx.info
        # Повертаємо той самий результат, що був раніше
        logger.warning(
            "Found duplicate transaction: ",
            extra=get_extra_data_log(existing_tx)
        )
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
    result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.user_id == user_id)
    )
    user_subscription: Subscription | None = result.scalar_one_or_none()

    # атомарна транзакція
    async with session.begin_nested():
        if not user_subscription:
            previous_tier = None
            user_subscription = Subscription(
                user_id=user_id, plan_id=payload.subscription_tier
            )
            session.add(user_subscription)
            plan = await session.get(SubscriptionPlan, payload.subscription_tier)
        else:
            previous_tier = user_subscription.plan.tier
            user_subscription.plan_id = payload.subscription_tier
            plan = user_subscription.plan

        # кредити
        credits_before = await balance_service.get_credits(user_id)
        balance_before = credits_before.balance
        user_credit = await balance_service.update_credits(
            user_id, payload.credits_to_add
        )
        balance_after = user_credit.balance

        new_tier = payload.subscription_tier
        multiplier = plan.multiplier
        purchase_rate = plan.purchase_rate
        credits_to_add = payload.credits_to_add
        operation_id = payload.operation_id
        tx_id = generate_transaction_id(operation_id)

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

        logger.info(
            f"Updated credits. Transaction:",
            extra=get_extra_data_log(new_tx)
        )

        session.add(new_tx)
        session.add(new_tx)
        await session.commit()

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
    description="Лише внутрішній доступ. Headers: X-Service-Token",
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
    session: AsyncSession = Depends(get_session),
    balance_service: BalanceService = Depends(get_balance_service)
):
    # перевірка user існує? як що ні: Exception
    await user_existing_check(session, user_id)

    # завантажуємо підписку разом із планом
    result = await session.execute(
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
    user_credits = await balance_service.get_credits(user_id)

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
    session: AsyncSession = Depends(get_session),
    balance_service: BalanceService = Depends(get_balance_service)
):
    # перевірка user існує? як що ні: Exception
    await user_existing_check(session, user_id)

    # завантажуємо підписку разом із планом
    result = await session.execute(
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
    user_credits = await balance_service.get_credits(user_id)
    balance = user_credits.balance

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
    session: AsyncSession = Depends(get_session),
    balance_service: BalanceService = Depends(get_balance_service)
):
    user_id = payload.user_id

    # перевірка user існує? як що ні: Exception
    await user_existing_check(session, user_id)

    # Перевіряємо ідемпотентність
    operation_id = payload.operation_id
    is_duplicate, existing_tx = await check_idempotency(
        session=session,
        operation_id=operation_id,
        expected_type=TransactionType.ADD.value
    )

    if is_duplicate and existing_tx is not None:
        metadata = existing_tx.info
        # Повертаємо той самий результат, що був раніше
        logger.warning(
            "Found duplicate transaction: ",
            extra=get_extra_data_log(existing_tx)
        )
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
    result = await session.execute(
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
    settings = await session.execute(select(Settings))
    settings = settings.scalars().first()
    if not settings:
        settings = Settings()
        session.add(settings)
        await session.commit()
    base_rate = settings.base_rate

    # розрахунок суми кредитів з урахуванням бонусу підписки
    amount_usd = payload.amount_usd
    credits_added = round(amount_usd * purchase_rate * base_rate)

    # кредити
    user_credits = await balance_service.get_credits(user_id)
    balance_before = user_credits.balance

    # оновити кредити та створити транзакцію
    async with session.begin_nested():
        # оновити кредити
        user_credits = await balance_service.update_credits(
            user_id, credits_added
        )
        balance_after = user_credits.balance

        id_tx = generate_transaction_id(operation_id)

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
            amount_usd=amount_usd,
            credits=credits_added,
            balance_before=balance_before,
            balance_after=balance_after,
            description=payload.description,
            created_at=datetime.now(timezone.utc),
            info=info
        )

        logger.info(
            f"Updated credits. Transaction:",
            extra=get_extra_data_log(new_tx)
        )

        session.add(new_tx)
        await session.commit()

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


@internal_router.post(
    "/credits/calculate",
    dependencies=[Depends(access_internal)],
    summary="Розрахунок вартості операції, без списання",
    description="Лише внутрішній доступ. Headers: X-Service-Token",
    response_model=CreditsCalculateResponse,
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
                    "examples": {
                        "user_not_found": {
                            "summary": "User not found",
                            "value": {"detail": "User not found."},
                        },
                        "no_subscription": {
                            "summary": "No subscription",
                            "value": {"detail": "User has no subscription."},
                        },
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
async def user_credits_calculate(
    payload: CreditsCalculateRequest,
    session: AsyncSession = Depends(get_session),
    balance_service: BalanceService = Depends(get_balance_service)
):
    user_id = payload.user_id

    # перевірка user існує? як що ні: Exception
    await user_existing_check(session, user_id)

    # отримуємо підписку і множник з плану
    result = await session.execute(
        select(Subscription, SubscriptionPlan.multiplier)
        .join(Subscription.plan)   # зв'язати з планом
        .where(Subscription.user_id == user_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' has no subscription.",
        )

    _, multiplier = row

    # отримати базову ставку
    base_rate = await get_base_rate_from_settings(session)

    # отримати баланс
    user_credits = await balance_service.get_credits(user_id)
    user_balance = user_credits.balance

    # розрахувати кредити до списання
    cost_usd = payload.cost_usd
    multiplier = float(multiplier)
    credits_to_charge = calculate_credits_amount(cost_usd, multiplier, base_rate)
    balance_before_charge = user_balance   # може бути нульовим (!)
    balance_after_charge = balance_before_charge - credits_to_charge

    return CreditsCalculateResponse(
        user_id=user_id,
        cost_usd=cost_usd,
        credits_to_charge=credits_to_charge,
        multiplier=multiplier,
        current_balance=balance_before_charge,
        balance_after=balance_after_charge,
        sufficient=(balance_after_charge >= 0)
    )


@internal_router.post(
    "/credits/charge",
    dependencies=[Depends(access_internal)],
    summary=" Списання кредитів: atomic операція",
    description="Лише внутрішній доступ. Headers: X-Service-Token",
    response_model=Union[
        CreditsChargeSuccessResponse, CreditsChargeNoSuccessResponse
    ],
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
                    "examples": {
                        "user_not_found": {
                            "summary": "User not found",
                            "value": {"detail": "User not found."},
                        },
                        "no_subscription": {
                            "summary": "No subscription",
                            "value": {"detail": "User has no subscription."},
                        },
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
async def user_credits_charge(
    payload: CreditsChargeRequest,
    session: AsyncSession = Depends(get_session),
    balance_service: BalanceService = Depends(get_balance_service)
):
    user_id = payload.user_id

    # перевірка user існує? як що ні: Exception
    await user_existing_check(session, user_id)

    # отримуємо підписку і множник з плану
    result = await session.execute(
        select(Subscription, SubscriptionPlan.multiplier)
        .join(Subscription.plan)   # зв'язати з планом
        .where(Subscription.user_id == user_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' has no subscription.",
        )

    _, multiplier = row

    # Перевіряємо ідемпотентність
    operation_id = payload.operation_id
    is_duplicate, existing_tx = await check_idempotency(
        session=session,
        operation_id=operation_id,
        expected_type=TransactionType.CHARGE.value
    )

    if is_duplicate and existing_tx is not None:
        # Повертаємо той самий результат, що був раніше
        logger.warning(
            "Found duplicate transaction: ",
            extra=get_extra_data_log(existing_tx)
        )
        return CreditsChargeSuccessResponse(
            transaction_id=existing_tx.id,
            user_id=existing_tx.user_id,
            cost_usd=existing_tx.cost_usd,
            credits_charged=existing_tx.credits,
            balance_before=existing_tx.balance_before,
            balance_after=existing_tx.balance_after,
            operation_id=operation_id
        )

    # отримати базову ставку
    base_rate = await get_base_rate_from_settings(session)

    # отримати баланс
    user_credits_before = await balance_service.get_credits(user_id)
    balance_before_charge = user_credits_before.balance

    # розрахувати кредити до списання
    cost_usd = payload.cost_usd
    multiplier = float(multiplier)
    credits_to_charge = calculate_credits_amount(cost_usd, multiplier, base_rate)

    if (balance_before_charge - credits_to_charge) < 0:
        return CreditsChargeNoSuccessResponse(
            error="insufficient_credits",
            user_id=user_id,
            required_credits=credits_to_charge,
            current_balance=balance_before_charge,
            deficit=(credits_to_charge - balance_before_charge)
        )

    # atomic operation (!) here: txn, credits
    async with session.begin_nested():
        # списати кредити з балансу user (update credits)
        user_credits = await balance_service.update_credits(
            user_id, -credits_to_charge
        )
        new_balance = user_credits.balance

        # створити транзакцію
        id_tx = generate_transaction_id(operation_id)
        new_tx = Transaction(
            id=id_tx,
            user_id=user_id,
            operation_id=operation_id,
            type=TransactionType.CHARGE,
            cost_usd=cost_usd,
            credits=-credits_to_charge,
            balance_before=balance_before_charge,
            balance_after=new_balance,
            description=payload.description,
            created_at=datetime.now(timezone.utc),
            info=payload.metadata
        )

        logger.info(
            f"Updated credits. Transaction:",
            extra=get_extra_data_log(new_tx)
        )

        session.add(new_tx)
        await session.commit()

    return CreditsChargeSuccessResponse(
        transaction_id=id_tx,
        user_id=user_id,
        cost_usd=cost_usd,
        credits_charged=credits_to_charge,
        balance_before=balance_before_charge,
        balance_after=new_balance,
        operation_id=operation_id
    )
