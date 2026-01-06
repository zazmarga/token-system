from app.core.database import SessionLocal


# Dependency для отримання сесії
def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()
