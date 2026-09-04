from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TASK_ENGINE_",
        env_file=".env",
        extra="ignore",
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
