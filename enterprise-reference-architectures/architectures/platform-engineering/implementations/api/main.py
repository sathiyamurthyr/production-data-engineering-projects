"""Sample API for Platform Engineering."""

from fastapi import FastAPI

app = FastAPI(title="Platform Engineering API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "platform-engineering"}
