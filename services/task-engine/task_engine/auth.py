from fastapi import Header, HTTPException, status

from task_engine.config import get_settings


def require_api_token(authorization: str | None = Header(default=None)) -> None:
    expected = get_settings().api_token
    if not expected:
        return
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token")
