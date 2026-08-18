"""Sample API for Data Fabric."""

from fastapi import FastAPI

app = FastAPI(title="Data Fabric API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "data-fabric"}
