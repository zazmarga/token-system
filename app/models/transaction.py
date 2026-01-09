import enum

from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, JSON, Enum, func, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class TransactionType(enum.Enum):
    CHARGE = "charge"        # списання (витрата)
    ADD = "add"              # поповнення
    SUBSCRIPTION = "subscription"  # нарахування при підписці

class TransactionSource(enum.Enum):
    PURCHASE = "purchase"    # покупка кредитів
    SUBSCRIPTION = "subscription"  # підписка
    BONUS = "bonus"          # бонусні кредити
    REFUND = "refund"        # повернення

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    type = Column(Enum(TransactionType), nullable=False)
    source = Column(Enum(TransactionSource), nullable=True)  # уточнення походження

    operation_id = Column(String, unique=True, nullable=False)  # для ідемпотентності
    cost_usd = Column(Float, nullable=True)
    credits = Column(Integer, nullable=False)  # + або - кількість
    balance_before = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)

    description = Column(String, nullable=True)
    info = Column(JSON, default={})   # metadata (!)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="transactions")
