"""Sample API for Telecom Platform."""

from fastapi import FastAPI

app = FastAPI(title="Telecom Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "telecom"}
