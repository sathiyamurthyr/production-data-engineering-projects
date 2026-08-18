"""Sample API for Enterprise Search."""

from fastapi import FastAPI

app = FastAPI(title="Enterprise Search API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "enterprise-search"}
