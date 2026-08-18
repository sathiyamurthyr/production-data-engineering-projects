"""Sample API for Observability Platform."""

from fastapi import FastAPI

app = FastAPI(title="Observability Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "observability-platform"}
