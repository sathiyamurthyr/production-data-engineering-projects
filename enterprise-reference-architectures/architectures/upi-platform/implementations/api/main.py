"""Sample API for UPI Platform."""

from fastapi import FastAPI

app = FastAPI(title="UPI Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "upi-platform"}
