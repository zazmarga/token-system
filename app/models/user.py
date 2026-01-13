from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)

    # один користувач має один запис у Subscription
    subscription = relationship(
        "Subscription", back_populates="user", uselist=False
    )

    # один користувач має один запис у Credits
    credit = relationship("Credits", back_populates="user", uselist=False)

    # один користувач має багато записів у Transaction
    transactions = relationship("Transaction", back_populates="user")

