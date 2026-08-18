"""Sample API for Retail Analytics."""

from fastapi import FastAPI

app = FastAPI(title="Retail Analytics API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "retail"}
