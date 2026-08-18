"""Sample API for Fraud Detection."""

from fastapi import FastAPI

app = FastAPI(title="Fraud Detection API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "fraud-detection"}
