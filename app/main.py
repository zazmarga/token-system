from fastapi import FastAPI
from app.core.database import Base, engine


Base.metadata.create_all(bind=engine)


app = FastAPI(title="Token System")


@app.get("/health")
def health():
    return {"status": "ok"}
