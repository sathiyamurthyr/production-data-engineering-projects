"""Sample API for Security Platform."""

from fastapi import FastAPI

app = FastAPI(title="Security Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "security-platform"}
