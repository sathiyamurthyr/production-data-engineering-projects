"""Sample API for Recommendation Engine."""

from fastapi import FastAPI

app = FastAPI(title="Recommendation Engine API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "recommendation-engine"}
