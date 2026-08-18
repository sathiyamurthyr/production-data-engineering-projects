"""Sample API for Clickstream Platform."""

from fastapi import FastAPI

app = FastAPI(title="Clickstream Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "clickstream-platform"}
