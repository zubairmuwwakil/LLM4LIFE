#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

if [[ -z "${OBSIDIAN_VAULT_PATH:-}" ]]; then
  echo "OBSIDIAN_VAULT_PATH is required." >&2
  exit 64
fi
if [[ -z "${OBSIDIAN_VAULT_SCOPE:-}" ]]; then
  echo "OBSIDIAN_VAULT_SCOPE is required (for example: primary-vault)." >&2
  exit 64
fi
TOKEN="${OBSIDIAN_BRIDGE_TOKEN:-}"
if [[ ${#TOKEN} -lt 32 ]]; then
  echo "OBSIDIAN_BRIDGE_TOKEN must be at least 32 characters." >&2
  exit 64
fi
if [[ -z "${OBSIDIAN_ALLOWED_PREFIXES:-}" && "${OBSIDIAN_BRIDGE_ALLOW_WHOLE_VAULT:-false}" != "true" ]]; then
  echo "Set OBSIDIAN_ALLOWED_PREFIXES, or explicitly opt into whole-vault access." >&2
  exit 64
fi

exec "${PYTHON:-python3}" scripts/obsidian_local_bridge.py "$@"
