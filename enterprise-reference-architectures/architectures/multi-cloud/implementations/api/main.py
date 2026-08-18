"""Sample API for Multi-Cloud Platform."""

from fastapi import FastAPI

app = FastAPI(title="Multi-Cloud Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "multi-cloud"}
