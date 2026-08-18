"""Sample API for Streaming Platform."""

from fastapi import FastAPI

app = FastAPI(title="Streaming Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "streaming-platform"}
