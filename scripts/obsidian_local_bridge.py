#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from people_obsidian_link import build_link_plan  # noqa: E402

MAX_BODY_BYTES = 64 * 1024
TOKEN_MIN_LENGTH = 32


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _allowed_prefixes(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    values: list[str] = []
    for item in raw.split(os.pathsep):
        item = item.strip().replace("\\", "/").strip("/")
        if item:
            values.append(item)
    return tuple(values)


def _safe_note(vault_root: Path, note_path: str, allowed_prefixes: tuple[str, ...]) -> tuple[Path, str]:
    relative = Path(note_path)
    if relative.is_absolute() or relative.suffix.lower() != ".md":
        raise ValueError("path must be a relative .md note path")
    if any(part.startswith(".") for part in relative.parts):
        raise ValueError("hidden vault paths are not accessible")

    root = vault_root.resolve()
    resolved = (root / relative).resolve()
    try:
        normalized = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("path escapes configured vault") from exc
    if not resolved.is_file():
        raise ValueError("note does not exist")

    if allowed_prefixes:
        allowed = any(
            normalized == prefix or normalized.startswith(prefix.rstrip("/") + "/")
            for prefix in allowed_prefixes
        )
        if not allowed:
            raise ValueError("note is outside OBSIDIAN_ALLOWED_PREFIXES")
    return resolved, normalized


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _path_hash(path: str) -> str:
    return hashlib.sha256(path.encode("utf-8")).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


class BridgeState:
    def __init__(
        self,
        *,
        vault_root: Path,
        vault_scope: str,
        token: str,
        allowed_prefixes: tuple[str, ...],
        audit_path: Path,
    ) -> None:
        self.vault_root = vault_root.resolve()
        self.vault_scope = vault_scope.strip()
        self.token = token
        self.allowed_prefixes = allowed_prefixes
        self.audit_path = audit_path

        if not self.vault_root.is_dir():
            raise ValueError("OBSIDIAN_VAULT_PATH must be an existing directory")
        if not self.vault_scope:
            raise ValueError("OBSIDIAN_VAULT_SCOPE is required")
        if len(self.token) < TOKEN_MIN_LENGTH:
            raise ValueError(f"OBSIDIAN_BRIDGE_TOKEN must be at least {TOKEN_MIN_LENGTH} characters")
        if not self.allowed_prefixes and not _bool_env("OBSIDIAN_BRIDGE_ALLOW_WHOLE_VAULT"):
            raise ValueError(
                "Set OBSIDIAN_ALLOWED_PREFIXES or explicitly set OBSIDIAN_BRIDGE_ALLOW_WHOLE_VAULT=true"
            )

    def authorized(self, header: str | None) -> bool:
        if not header or not header.startswith("Bearer "):
            return False
        supplied = header[len("Bearer ") :]
        return hmac.compare_digest(supplied, self.token)

    def note(self, note_path: str) -> tuple[Path, str]:
        return _safe_note(self.vault_root, note_path, self.allowed_prefixes)

    def audit(self, *, action: str, status: str, normalized_path: str | None = None) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "at": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "status": status,
            "path_sha256": _path_hash(normalized_path) if normalized_path else None,
            "content_recorded": False,
        }
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")


class ObsidianBridgeHandler(BaseHTTPRequestHandler):
    server_version = "LLM4LIFEObsidianBridge/1"

    @property
    def state(self) -> BridgeState:
        return self.server.state  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        # Avoid leaking private paths/query strings into terminal/web-server logs.
        return

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _require_auth(self) -> bool:
        if self.state.authorized(self.headers.get("Authorization")):
            return True
        self.state.audit(action="auth", status="denied")
        self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        return False

    def _read_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("Content-Length is required")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length < 0 or length > MAX_BODY_BYTES:
            raise ValueError("request body exceeds limit")
        raw = self.rfile.read(length)
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send(HTTPStatus.OK, {"ok": True, "bridge": "obsidian_local_v1"})
            return
        if parsed.path != "/v1/note":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if not self._require_auth():
            return

        normalized: str | None = None
        try:
            values = parse_qs(parsed.query, keep_blank_values=True)
            note_path = (values.get("path") or [""])[0]
            note_file, normalized = self.state.note(note_path)
            data = note_file.read_bytes()
            self.state.audit(action="note_read", status="succeeded", normalized_path=normalized)
            self._send(
                HTTPStatus.OK,
                {
                    "path": normalized,
                    "sha256": _sha256_bytes(data),
                    "content": data.decode("utf-8"),
                },
            )
        except (ValueError, UnicodeDecodeError) as exc:
            self.state.audit(action="note_read", status="rejected", normalized_path=normalized)
            self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid_request", "message": str(exc)})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/v1/people/link":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if not self._require_auth():
            return

        normalized: str | None = None
        try:
            payload = self._read_json()
            note_path = str(payload.get("path") or "")
            person_id = str(payload.get("person_id") or "")
            expected_sha256 = str(payload.get("expected_sha256") or "")
            if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
                raise ValueError("expected_sha256 is required for optimistic concurrency")

            note_file, normalized = self.state.note(note_path)
            before = note_file.read_bytes()
            actual = _sha256_bytes(before)
            if not hmac.compare_digest(actual.lower(), expected_sha256.lower()):
                self.state.audit(action="people_link", status="precondition_failed", normalized_path=normalized)
                self._send(
                    HTTPStatus.PRECONDITION_FAILED,
                    {"error": "sha256_mismatch", "current_sha256": actual},
                )
                return

            plan, receipt = build_link_plan(
                vault_root=self.state.vault_root,
                manifest={
                    "vault_scope": self.state.vault_scope,
                    "links": [{"person_id": person_id, "note_path": normalized}],
                },
                apply_frontmatter=True,
            )
            after = note_file.read_bytes()
            external_id = plan["refs"][0]["external_id"]
            note_id = external_id.removeprefix("note:")
            self.state.audit(action="people_link", status="succeeded", normalized_path=normalized)
            self._send(
                HTTPStatus.OK,
                {
                    "linked": True,
                    "note_id": note_id,
                    "sha256": _sha256_bytes(after),
                    "changed": bool(receipt["notes_changed_or_would_change"]),
                    "narrative_copied": False,
                },
            )
        except (ValueError, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            self.state.audit(action="people_link", status="rejected", normalized_path=normalized)
            self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid_request", "message": str(exc)})


class ObsidianBridgeServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], state: BridgeState):
        super().__init__(address, ObsidianBridgeHandler)
        self.state = state


def build_state_from_env() -> BridgeState:
    vault_path = os.environ.get("OBSIDIAN_VAULT_PATH")
    token = os.environ.get("OBSIDIAN_BRIDGE_TOKEN") or ""
    vault_scope = os.environ.get("OBSIDIAN_VAULT_SCOPE") or ""
    if not vault_path:
        raise ValueError("OBSIDIAN_VAULT_PATH is required")
    return BridgeState(
        vault_root=Path(vault_path),
        vault_scope=vault_scope,
        token=token,
        allowed_prefixes=_allowed_prefixes(os.environ.get("OBSIDIAN_ALLOWED_PREFIXES")),
        audit_path=Path(
            os.environ.get("OBSIDIAN_BRIDGE_AUDIT_PATH", ".private/obsidian-bridge/audit.jsonl")
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the localhost-only LLM4LIFE Obsidian bridge")
    parser.add_argument("--port", type=int, default=int(os.environ.get("OBSIDIAN_BRIDGE_PORT", "8765")))
    args = parser.parse_args()

    state = build_state_from_env()
    # V1 is deliberately localhost-only. Remote exposure requires a separate, explicit secure transport decision.
    server = ObsidianBridgeServer(("127.0.0.1", args.port), state)
    print(json.dumps({"listening": f"http://127.0.0.1:{args.port}", "vault_scope": state.vault_scope}))
    server.serve_forever()


if __name__ == "__main__":
    main()
