#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--apply" ]]; then
  echo "Usage: bash scripts/run_apple_google_phase2.sh --apply" >&2
  echo "This performs the already-approved non-destructive Apple -> Google Contacts migration. It does not delete contacts." >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PRIVATE=".private/people"
mkdir -p "$PRIVATE"

VCARD="$PRIVATE/apple_contacts.vcf"
if [[ ! -f "$VCARD" ]]; then
  shopt -s nullglob
  candidates=("$PRIVATE"/*.vcf)
  shopt -u nullglob
  if [[ "${#candidates[@]}" -eq 1 ]]; then
    VCARD="${candidates[0]}"
  else
    echo "Apple vCard not found." >&2
    echo "Put it at $PRIVATE/apple_contacts.vcf, or keep exactly one .vcf file in $PRIVATE/." >&2
    exit 2
  fi
fi

CLIENT="$PRIVATE/google-oauth-client.json"
TOKEN="$PRIVATE/google-people-token.json"
SNAPSHOT="$PRIVATE/google_people_live.json"
PLAN="$PRIVATE/apple_google_plan.json"
RECEIPT="$PRIVATE/apple_google_apply_receipt.json"
REFRESHED="$PRIVATE/google_people_live_after_apple.json"

[[ -f "$CLIENT" ]] || { echo "Missing $CLIENT" >&2; exit 2; }
[[ -f "$TOKEN" ]] || { echo "Missing $TOKEN. Run the Google People enumerate bootstrap first." >&2; exit 2; }

PYTHON="${PYTHON:-python}"
command -v "$PYTHON" >/dev/null 2>&1 || { echo "Python command '$PYTHON' not found." >&2; exit 2; }

# 1) Refresh the complete saved-contact snapshot immediately before planning so
#    Apple-only records are not created from stale provider state.
"$PYTHON" scripts/google_people_phase2.py enumerate \
  --account-scope google-primary \
  --client-secret "$CLIENT" \
  --token "$TOKEN" \
  --output "$SNAPSHOT"

# 2) Regenerate the deterministic private plan from the exact current provider
#    snapshot and Apple export.
"$PYTHON" scripts/apple_google_phase2.py plan \
  --apple-vcard "$VCARD" \
  --google-snapshot "$SNAPSHOT" \
  --output "$PLAN"

# 3) Validate source digests and the plan with no provider writes.
"$PYTHON" scripts/apple_google_phase2.py apply \
  --plan "$PLAN" \
  --apple-vcard "$VCARD" \
  --google-snapshot "$SNAPSHOT" \
  --receipt "$RECEIPT" \
  --client-secret "$CLIENT" \
  --token "$TOKEN" \
  --refreshed-snapshot "$REFRESHED"

# 4) Apply only the migration helper's non-destructive create/update operations.
#    The helper has no provider-contact delete endpoint and writes a resumable
#    private receipt after each operation.
"$PYTHON" scripts/apple_google_phase2.py apply \
  --plan "$PLAN" \
  --apple-vcard "$VCARD" \
  --google-snapshot "$SNAPSHOT" \
  --receipt "$RECEIPT" \
  --client-secret "$CLIENT" \
  --token "$TOKEN" \
  --refreshed-snapshot "$REFRESHED" \
  --apply

echo
echo "Apple -> Google Contacts migration apply completed."
echo "Private receipt: $RECEIPT"
echo "Refreshed Google snapshot: $REFRESHED"
