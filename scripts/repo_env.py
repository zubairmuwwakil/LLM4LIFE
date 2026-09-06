#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path

_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = REPO_ROOT / ".env"


def _decode_value(raw: str) -> str:
    value = raw.strip()
    if not value:
        return ""

    if value[0] in {"'", '"'}:
        quote = value[0]
        escaped = False
        out: list[str] = []
        for idx in range(1, len(value)):
            char = value[idx]
            if quote == '"' and char == "\\" and not escaped:
                escaped = True
                continue
            if char == quote and not escaped:
                trailing = value[idx + 1 :].strip()
                if trailing and not trailing.startswith("#"):
                    raise ValueError("Unexpected content after quoted .env value")
                return "".join(out)
            if escaped:
                translations = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}
                out.append(translations.get(char, char))
                escaped = False
            else:
                out.append(char)
        raise ValueError("Unterminated quoted .env value")

    # Inline comments are recognized only when preceded by whitespace, so URLs/fragments remain intact.
    match = re.search(r"\s+#", value)
    if match:
        value = value[: match.start()].rstrip()
    return value


def read_env_file(path: Path = DEFAULT_ENV_PATH) -> dict[str, str]:
    if not path.is_file():
        return {}

    values: dict[str, str] = {}
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            raise ValueError(f"Invalid .env line {line_no}: expected KEY=VALUE")
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not _KEY.fullmatch(key):
            raise ValueError(f"Invalid .env key on line {line_no}")
        values[key] = _decode_value(raw_value)
    return values


def load_repo_env(*, override: bool = False, path: Path = DEFAULT_ENV_PATH) -> dict[str, str]:
    """Load repo-local .env without executing shell code.

    Existing process environment wins by default so one-off shell overrides remain possible.
    Returns the parsed file values for diagnostics/tests without exposing them to logs.
    """
    values = read_env_file(path)
    for key, value in values.items():
        if override or key not in os.environ:
            os.environ[key] = value
    return values
