"""Sample API for Manufacturing Platform."""

from fastapi import FastAPI

app = FastAPI(title="Manufacturing Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "manufacturing"}
