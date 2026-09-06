#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import secrets
from pathlib import Path

from repo_env import DEFAULT_ENV_PATH, read_env_file

MANAGED_KEYS = (
    "OBSIDIAN_VAULT_PATH",
    "OBSIDIAN_VAULT_SCOPE",
    "OBSIDIAN_BRIDGE_TOKEN",
    "OBSIDIAN_BRIDGE_PORT",
    "OBSIDIAN_ALLOWED_PREFIXES",
    "OBSIDIAN_BRIDGE_ALLOW_WHOLE_VAULT",
    "OBSIDIAN_BRIDGE_AUDIT_PATH",
)

DEFAULTS = {
    "OBSIDIAN_VAULT_SCOPE": "primary-vault",
    "OBSIDIAN_BRIDGE_PORT": "8765",
    "OBSIDIAN_BRIDGE_ALLOW_WHOLE_VAULT": "false",
    "OBSIDIAN_BRIDGE_AUDIT_PATH": ".private/obsidian-bridge/audit.jsonl",
}


def _quote(value: str) -> str:
    if not value:
        return ""
    if re.fullmatch(r"[A-Za-z0-9_./:@%+,-]+", value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _upsert_env_file(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else [
        "# LLM4LIFE local runtime configuration",
        "# Private: this file is gitignored. Do not commit it.",
        "",
    ]
    remaining = dict(updates)
    output: list[str] = []
    pattern = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
    for line in lines:
        match = pattern.match(line)
        key = match.group(1) if match else None
        if key in remaining:
            output.append(f"{key}={_quote(remaining.pop(key))}")
        else:
            output.append(line)
    if remaining:
        if output and output[-1] != "":
            output.append("")
        output.append("# Obsidian bridge")
        for key in MANAGED_KEYS:
            if key in remaining:
                output.append(f"{key}={_quote(remaining.pop(key))}")
        for key, value in remaining.items():
            output.append(f"{key}={_quote(value)}")
    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def initialize(*, path: Path, capture_current: bool, rotate_bridge_token: bool) -> dict[str, bool]:
    existing = read_env_file(path)
    updates: dict[str, str] = {}

    for key, value in DEFAULTS.items():
        if not existing.get(key):
            updates[key] = value

    if capture_current:
        for key in MANAGED_KEYS:
            current = os.environ.get(key)
            if current and not existing.get(key):
                updates[key] = current

    token_present = bool(existing.get("OBSIDIAN_BRIDGE_TOKEN"))
    if rotate_bridge_token or not token_present:
        updates["OBSIDIAN_BRIDGE_TOKEN"] = secrets.token_hex(32)
        token_present = True

    _upsert_env_file(path, updates)
    final = read_env_file(path)
    return {
        "env_file_exists": path.is_file(),
        "permissions_owner_only": (path.stat().st_mode & 0o077) == 0,
        "vault_path_present": bool(final.get("OBSIDIAN_VAULT_PATH")),
        "vault_scope_present": bool(final.get("OBSIDIAN_VAULT_SCOPE")),
        "bridge_token_present": bool(final.get("OBSIDIAN_BRIDGE_TOKEN")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create/update the private repo .env and persist Obsidian runtime settings safely."
    )
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_PATH))
    parser.add_argument(
        "--capture-current",
        action="store_true",
        help="Persist currently exported OBSIDIAN_* values that are missing from .env.",
    )
    parser.add_argument(
        "--rotate-bridge-token",
        action="store_true",
        help="Generate a new bridge token and replace the saved one without printing it.",
    )
    args = parser.parse_args()

    status = initialize(
        path=Path(args.env_file),
        capture_current=args.capture_current,
        rotate_bridge_token=args.rotate_bridge_token,
    )
    print("LLM4LIFE local .env initialized (secret values not printed).")
    for key, value in status.items():
        print(f"{key}: {'yes' if value else 'no'}")
    if not status["vault_path_present"]:
        print("Next: add OBSIDIAN_VAULT_PATH to .env (or rerun with --capture-current while it is exported).")


if __name__ == "__main__":
    main()
