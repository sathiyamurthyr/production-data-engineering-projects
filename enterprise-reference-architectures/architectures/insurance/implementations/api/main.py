"""Sample API for Insurance Platform."""

from fastapi import FastAPI

app = FastAPI(title="Insurance Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "insurance"}
