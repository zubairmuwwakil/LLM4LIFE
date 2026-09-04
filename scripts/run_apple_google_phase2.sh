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

# 0) If an earlier run stopped on an ambiguous 5xx createContact response,
#    reconcile that receipt against the PREVIOUS source snapshot before we
#    overwrite the snapshot. This prevents a blind retry from duplicating a
#    contact that Google may already have committed.
if [[ -f "$RECEIPT" && -f "$SNAPSHOT" ]]; then
  echo "Recovering any ambiguous prior createContact result..."
  "$PYTHON" scripts/apple_google_phase2_resilient.py recover \
    --apple-vcard "$VCARD" \
    --google-snapshot "$SNAPSHOT" \
    --receipt "$RECEIPT" \
    --client-secret "$CLIENT" \
    --token "$TOKEN"
fi

# 1) Refresh the complete saved-contact snapshot immediately before planning so
#    Apple-only records are not created from stale provider state.
echo "Refreshing Google Contacts snapshot..."
"$PYTHON" scripts/google_people_phase2.py enumerate \
  --account-scope google-primary \
  --client-secret "$CLIENT" \
  --token "$TOKEN" \
  --output "$SNAPSHOT"

# 2) Regenerate the deterministic private plan from the exact current provider
#    snapshot and Apple export.
echo "Regenerating migration plan..."
"$PYTHON" scripts/apple_google_phase2.py plan \
  --apple-vcard "$VCARD" \
  --google-snapshot "$SNAPSHOT" \
  --output "$PLAN"

# 3) Validate source digests and the plan with no provider writes.
echo "Validating migration plan..."
"$PYTHON" scripts/apple_google_phase2_resilient.py apply \
  --plan "$PLAN" \
  --apple-vcard "$VCARD" \
  --google-snapshot "$SNAPSHOT" \
  --receipt "$RECEIPT" \
  --client-secret "$CLIENT" \
  --token "$TOKEN" \
  --refreshed-snapshot "$REFRESHED"

# 4) Apply only the migration helper's non-destructive create/update operations.
#    New creates use deterministic temporary markers so transient 5xx/network
#    failures can be resolved before any retry. No provider delete endpoint exists.
echo "Applying migration (resumable; this can take several minutes)..."
"$PYTHON" scripts/apple_google_phase2_resilient.py apply \
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
