from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from task_engine.api.routes import router
from task_engine.config import get_settings
from task_engine.cron import router as cron_router
from task_engine.database import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.auto_create_schema:
        # Explicit development-only convenience. Production schema changes use Alembic.
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="LLM4LIFE Task Engine",
    version="0.2.0",
    description="Cross-system task execution lifecycle, follow-up, and scheduling coordination.",
    lifespan=lifespan,
)
app.include_router(router)
app.include_router(cron_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
