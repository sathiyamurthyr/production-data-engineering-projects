"""Sample API for Enterprise Capstone."""

from fastapi import FastAPI

app = FastAPI(title="Enterprise Capstone API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "enterprise-capstone"}
