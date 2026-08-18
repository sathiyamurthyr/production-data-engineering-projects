"""Sample API for Marketing Analytics."""

from fastapi import FastAPI

app = FastAPI(title="Marketing Analytics API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "marketing-analytics"}
