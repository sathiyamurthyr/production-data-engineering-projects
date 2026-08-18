"""Sample API for Lakehouse Platform."""

from fastapi import FastAPI

app = FastAPI(title="Lakehouse Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "lakehouse"}
