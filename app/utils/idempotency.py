from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction


async def check_idempotency(
    db: AsyncSession,
    operation_id: str,
    expected_type: Optional[str] = None,
) -> Tuple[bool, Optional[Transaction]]:
    """
    Перевіряє, чи вже існує транзакція з таким operation_id
    Повертає:
        (is_duplicate: bool, existing_transaction: Transaction | None)
    Якщо is_duplicate == True - операцію вже виконували раніше
    Якщо expected_type передано і тип не збігається - кидає 409
    """
    result = await db.execute(
        select(Transaction).where(Transaction.operation_id == operation_id)
    )
    tx: Transaction | None = result.scalar_one_or_none()

    if not tx:
        return False, None

    # Якщо є очікуваний тип операції — перевіряємо
    if expected_type is not None and tx.type.value != expected_type:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Operation ID '{operation_id}' already used "
                f"for different operation type: {tx.type.value}"
            )
        )

    return True, tx
