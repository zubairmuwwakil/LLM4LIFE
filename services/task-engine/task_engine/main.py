from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from task_engine.api.routes import router
from task_engine.database import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Development convenience. Production schema changes use Alembic migrations.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="LLM4LIFE Task Engine",
    version="0.1.0",
    description="Cross-system task execution lifecycle, follow-up, and scheduling coordination.",
    lifespan=lifespan,
)
app.include_router(router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
