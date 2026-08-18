"""Sample API for Digital Wallet."""

from fastapi import FastAPI

app = FastAPI(title="Digital Wallet API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "digital-wallet"}
