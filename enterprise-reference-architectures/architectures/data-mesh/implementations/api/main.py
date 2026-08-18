"""Sample API for Data Mesh."""

from fastapi import FastAPI

app = FastAPI(title="Data Mesh API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "data-mesh"}
