from sqlalchemy import Column, Integer

from app.core.database import Base


class User(Base):
	__tablename__ = "user"

	id = Column(Integer, primary_key=True, index=True)

	@property
	def public_id(self) -> str:
		return f"user_{self.id}"
