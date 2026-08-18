"""Sample API for Logistics Platform."""

from fastapi import FastAPI

app = FastAPI(title="Logistics Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "logistics"}
