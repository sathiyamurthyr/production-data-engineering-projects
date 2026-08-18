"""Sample API for IoT Platform."""

from fastapi import FastAPI

app = FastAPI(title="IoT Platform API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "iot-platform"}
