"""Sample API for E-Commerce Platform."""

from fastapi import FastAPI

app = FastAPI(title="E-Commerce Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "ecommerce"}
