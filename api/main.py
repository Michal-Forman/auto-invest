# Standard library
import os

# Third-party
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Local
from api.routers import (
    analytics,
    config,
    health,
    instruments,
    invest,
    orders,
    preview,
    profile,
    runs,
)

app = FastAPI(title="auto-invest API", version="1.0.0")

origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:5174",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(config.router)
app.include_router(runs.router)
app.include_router(orders.router)
app.include_router(instruments.router)
app.include_router(preview.router)
app.include_router(invest.router)
app.include_router(analytics.router)
app.include_router(profile.router)
