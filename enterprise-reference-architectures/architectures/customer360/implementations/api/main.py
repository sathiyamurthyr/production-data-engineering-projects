"""Sample API for Customer 360."""

from fastapi import FastAPI

app = FastAPI(title="Customer 360 API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "customer360"}
