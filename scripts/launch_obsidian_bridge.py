#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import runpy
import socket
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from repo_env import load_repo_env


def _health(port: int) -> dict[str, object] | None:
    try:
        with urlopen(f"http://127.0.0.1:{port}/health", timeout=0.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else None
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return None


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _requested_port(argv: list[str]) -> int:
    for idx, arg in enumerate(argv):
        if arg.startswith("--port="):
            return int(arg.split("=", 1)[1])
        if arg == "--port":
            if idx + 1 >= len(argv):
                raise SystemExit("--port requires a value")
            return int(argv[idx + 1])
    return int(os.environ.get("OBSIDIAN_BRIDGE_PORT", "8765"))


def main() -> None:
    load_repo_env()
    port = _requested_port(sys.argv[1:])
    if _port_in_use(port):
        health = _health(port)
        if health and health.get("bridge") == "obsidian_local_v1":
            raise SystemExit(
                f"LLM4LIFE Obsidian bridge is already running on 127.0.0.1:{port}. "
                "If its old token was not saved, stop that old bridge process and restart this command; "
                "the persisted token from .env will then be used."
            )
        raise SystemExit(
            f"Port {port} is already in use by another process. "
            f"Inspect it with: lsof -nP -iTCP:{port} -sTCP:LISTEN"
        )

    target = Path(__file__).resolve().parent / "obsidian_local_bridge.py"
    sys.argv = [str(target), *sys.argv[1:]]
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
