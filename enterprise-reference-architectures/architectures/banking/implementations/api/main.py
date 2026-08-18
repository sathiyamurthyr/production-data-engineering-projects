"""Sample API for Global Banking."""

from fastapi import FastAPI

app = FastAPI(title="Global Banking API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "banking"}
