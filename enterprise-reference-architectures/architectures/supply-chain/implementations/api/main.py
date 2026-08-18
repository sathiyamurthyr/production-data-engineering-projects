"""Sample API for Supply Chain Platform."""

from fastapi import FastAPI

app = FastAPI(title="Supply Chain Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "supply-chain"}
