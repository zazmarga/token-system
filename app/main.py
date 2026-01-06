from fastapi import FastAPI
app = FastAPI(title="Token System")

@app.get("/health")
def health():
    return {"status": "ok"}
