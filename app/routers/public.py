from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.models import TransactionSource
from app.models.subscription import SubscriptionPlan
from app.schemas.credits import CreditsPurchaseResponse, CreditsPurchasePayload
from app.schemas.subscription import SubscriptionPlanPublicList
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
    db: AsyncSession = Depends(get_db)
):
    query = select(SubscriptionPlan).where(SubscriptionPlan.active.is_(True))

    result = await db.execute(query)
    plans = result.scalars().all()

    return SubscriptionPlanPublicList(plans=plans)


@public_router.post(
    "/credits/purchase",
    # dependencies=[Depends(get_current_user)],
    summary="Поповнення кредитів",
    description="Доступ для user з token. Headers: Authorization: Bearer {user_token}",
    response_model=CreditsPurchaseResponse,
    status_code=status.HTTP_200_OK,
    responses={
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
        db: AsyncSession = Depends(get_db)
):
    source = TransactionSource.PURCHASE.value

    if not is_payment_complete(payload.payment_method_id):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Payment '{payload.payment_method_id}' not completed."
        )

    operation_id = await generate_operation_id(db, source=source)

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
