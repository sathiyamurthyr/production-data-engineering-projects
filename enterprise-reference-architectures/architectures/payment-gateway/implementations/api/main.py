"""Sample API for Payment Gateway."""

from fastapi import FastAPI

app = FastAPI(title="Payment Gateway API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "payment-gateway"}
