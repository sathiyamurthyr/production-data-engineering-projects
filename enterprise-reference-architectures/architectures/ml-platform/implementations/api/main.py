"""Sample API for ML Platform."""

from fastapi import FastAPI

app = FastAPI(title="ML Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "ml-platform"}
