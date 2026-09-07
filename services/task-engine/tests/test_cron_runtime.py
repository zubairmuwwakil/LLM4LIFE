import pytest
from fastapi import HTTPException

from task_engine.config import Settings
from task_engine.cron import _authorize_cron, missing_runtime_configuration


def production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "postgresql+psycopg://runtime@example/task_engine",
        "canonical_database_url": "postgresql://runtime@example/neondb",
        "google_client_id": "client",
        "google_client_secret": "secret",
        "google_refresh_token": "refresh",
        "cron_secret": "cron-secret",
    }
    values.update(overrides)
    return Settings(**values)


def test_runtime_readiness_is_clean_when_all_required_values_exist() -> None:
    assert missing_runtime_configuration(production_settings()) == []


def test_runtime_readiness_fails_closed_for_sqlite_and_missing_provider_credentials() -> None:
    settings = production_settings(
        database_url="sqlite:///./task-engine.db",
        google_refresh_token=None,
        cron_secret=None,
    )

    assert missing_runtime_configuration(settings) == [
        "TASK_ENGINE_DATABASE_URL",
        "TASK_ENGINE_GOOGLE_REFRESH_TOKEN",
        "CRON_SECRET",
    ]


def test_cron_authorization_accepts_only_exact_bearer_secret() -> None:
    settings = production_settings()
    _authorize_cron("Bearer cron-secret", settings)

    with pytest.raises(HTTPException) as exc_info:
        _authorize_cron("Bearer wrong", settings)
    assert exc_info.value.status_code == 401

    with pytest.raises(HTTPException) as exc_info:
        _authorize_cron(None, settings)
    assert exc_info.value.status_code == 401


def test_cron_authorization_is_unavailable_when_secret_is_not_configured() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _authorize_cron("Bearer anything", production_settings(cron_secret=None))

    assert exc_info.value.status_code == 503


def test_existing_google_environment_names_are_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TASK_ENGINE_GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("TASK_ENGINE_GOOGLE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("TASK_ENGINE_GOOGLE_REFRESH_TOKEN", raising=False)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "shared-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "shared-secret")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "shared-refresh")

    settings = Settings(_env_file=None)

    assert settings.google_client_id == "shared-client"
    assert settings.google_client_secret == "shared-secret"
    assert settings.google_refresh_token == "shared-refresh"
