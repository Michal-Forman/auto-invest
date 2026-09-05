# Standard library
import asyncio
from contextlib import asynccontextmanager
import os
from typing import AsyncIterator

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
from core.log import log
from core.pending_investments import retry_pending_investments

PENDING_CHECK_INTERVAL_SECONDS = 3600


async def _pending_investment_loop() -> None:
    """Retry pending one-time investments on a timer for the life of the process."""
    while True:
        try:
            await asyncio.to_thread(retry_pending_investments)
        except Exception as e:
            log.error(f"Pending investment sweep failed: {e}")
        await asyncio.sleep(PENDING_CHECK_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(_pending_investment_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="auto-invest API", version="1.0.0", lifespan=lifespan)

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
