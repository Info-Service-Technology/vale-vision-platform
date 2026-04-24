from fastapi import FastAPI
from app.api.routes import health, events

app = FastAPI(title="Vale Vision API", version="0.1.0")
app.include_router(health.router, prefix="/api")
app.include_router(events.router, prefix="/api")
