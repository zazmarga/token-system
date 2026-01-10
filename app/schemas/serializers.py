from app.models import Transaction, TransactionType
from app.schemas.transactions import (
	TransactionDetail, ChargeTransaction, AddTransaction,
    SubscriptionTransaction
)


def serialize_transaction(tx: Transaction) -> TransactionDetail:
    tx_dict = {
        "id": tx.id,
        "type": tx.type.value,
        "created_at": tx.created_at,
        "credits": tx.credits,
        "balance_after": tx.balance_after,
        "description": tx.description,
        "operation_id": tx.operation_id,
        "cost_usd": tx.cost_usd,
        "amount_usd": tx.amount_usd,
    }

    if tx.type == TransactionType.CHARGE:
        return ChargeTransaction.model_validate(tx_dict)
    elif tx.type == TransactionType.ADD:
        return AddTransaction.model_validate(tx_dict)
    elif tx.type == TransactionType.SUBSCRIPTION:
        return SubscriptionTransaction.model_validate(tx_dict)
