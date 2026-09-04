#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

PRIVATE_DIR=".private/people"
GOOGLE_SNAPSHOT="${PRIVATE_DIR}/google_people_live_after_apple.json"
APPLE_SNAPSHOT="${PRIVATE_DIR}/apple_contacts_live.json"
RECEIPT="${PRIVATE_DIR}/apple_google_sync_verification_receipt.json"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Apple Contacts sync verification must run on macOS." >&2
  exit 64
fi

if [[ ! -s "${GOOGLE_SNAPSHOT}" ]]; then
  echo "Missing post-cutover Google snapshot: ${GOOGLE_SNAPSHOT}" >&2
  exit 66
fi

mkdir -p "${PRIVATE_DIR}"

if command -v xcrun >/dev/null 2>&1 && xcrun --find swift >/dev/null 2>&1; then
  xcrun swift scripts/apple_contacts_live_export.swift "${APPLE_SNAPSHOT}"
elif command -v swift >/dev/null 2>&1; then
  swift scripts/apple_contacts_live_export.swift "${APPLE_SNAPSHOT}"
else
  echo "Swift is required. Install the Xcode Command Line Tools, then rerun." >&2
  exit 69
fi

"${PYTHON:-python3}" scripts/verify_apple_google_sync.py \
  --google-snapshot "${GOOGLE_SNAPSHOT}" \
  --apple-snapshot "${APPLE_SNAPSHOT}" \
  --receipt "${RECEIPT}" \
  --min-coverage 0.98 \
  --max-core-field-loss-rate 0.01

echo "Apple Contacts sync verification passed."
echo "Private receipt: ${RECEIPT}"
