"""Sample API for AI Knowledge Platform."""

from fastapi import FastAPI

app = FastAPI(title="AI Knowledge Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-knowledge-platform"}
