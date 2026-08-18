"""Sample API for Metadata Platform."""

from fastapi import FastAPI

app = FastAPI(title="Metadata Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "metadata-platform"}
