from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TASK_ENGINE_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    database_url: str = "sqlite:///./task-engine.db"
    timezone: str = "America/Toronto"
    followup_delay_minutes: int = Field(default=60, ge=1, le=1440)
    misses_before_review: int = Field(default=3, ge=1, le=20)
    auto_reschedule_horizon_days: int = Field(default=7, ge=1, le=30)
    movable_window_start_hour: int = Field(default=13, ge=0, le=23)
    movable_window_end_hour: int = Field(default=21, ge=1, le=24)
    high_stakes_threshold: int = Field(default=70, ge=0, le=100)
    api_token: str | None = None

    # Never let production application startup mutate schema implicitly. Local
    # development may opt in explicitly; production uses Alembic only.
    auto_create_schema: bool = False

    # Vercel injects CRON_SECRET into the Authorization header for Cron Jobs.
    # Accept both names so non-Vercel runtimes can keep the TASK_ENGINE_ prefix.
    cron_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TASK_ENGINE_CRON_SECRET", "CRON_SECRET"),
    )

    # Deterministic command worker. Keep canonical and provider credentials separate
    # from the Task Engine coordination database so permissions can remain narrow.
    canonical_database_url: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_refresh_token: str | None = None
    google_calendar_api_base: str = "https://www.googleapis.com/calendar/v3"
    google_oauth_token_url: str = "https://oauth2.googleapis.com/token"
    worker_lease_seconds: int = Field(default=120, ge=30, le=900)
    worker_max_attempts: int = Field(default=8, ge=1, le=30)
    worker_retry_base_seconds: int = Field(default=15, ge=1, le=3600)
    worker_retry_max_seconds: int = Field(default=1800, ge=30, le=86400)
    worker_batch_size: int = Field(default=20, ge=1, le=100)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
