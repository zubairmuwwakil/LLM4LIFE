#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Rebuild the private structured-memory candidate file without prompting for dates.
python3 scripts/people_structured_memory_review.py build
# Add profile Family & Friends relationship candidates and prompt only resolved edges.
python3 scripts/people_profile_relationship_review.py --interactive
python3 scripts/people_structured_memory_review.py validate
python3 scripts/import_people_structured_memory.py

echo
echo "People relationship review complete."
echo "The Neon step above was DRY-RUN ONLY; no relationship rows were written."
echo "Unresolved names remain private review candidates and never enter the graph."
echo "Review .private/people/structured_memory_neon_import_receipt.json before any apply step."
