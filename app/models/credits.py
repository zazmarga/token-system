
from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Credits(Base):
	__tablename__ = "credits"

	id = Column(Integer, primary_key=True)
	user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
	balance = Column(Integer, default=0) # поточний баланс
	total_earned = Column(Integer, default=0) # скільки всього нараховано
	total_spent = Column(Integer, default=0) # скільки всього списано

	user = relationship("User", back_populates="credit")
