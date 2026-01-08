from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # один користувач має один запис у Subscription
    subscription = relationship("Subscription", back_populates="user", uselist=False)

    # один користувач має один запис у Credits
    credit = relationship("Credits", back_populates="user", uselist=False)

    # один користувач має багато записів у Transaction
    transactions = relationship("Transaction", back_populates="user")

    @property
    def user_id(self) -> str:
        return f"user_{self.id}"
