#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 scripts/people_structured_memory_review.py build --interactive
python3 scripts/people_structured_memory_review.py validate
python3 scripts/import_people_structured_memory.py

echo
echo "Structured People memory review complete."
echo "The Neon step above was DRY-RUN ONLY; no date or relationship rows were written."
echo "Review .private/people/structured_memory_neon_import_receipt.json before any apply step."
