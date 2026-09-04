#!/usr/bin/env python3
"""Remove temporary LLM4LIFE People migration markers after durable receipt success.

This is non-destructive: it removes only the exact temporary marker key/value
added by apple_google_phase2_resilient.py and preserves every other userDefined
entry. No contact delete endpoint is implemented.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import apple_google_phase2 as base
from apple_google_phase2_resilient import MARKER_KEY, marker_value
from google_people_phase2 import enumerate_saved_contacts, write_snapshot

RETRYABLE = {429, 500, 502, 503, 504}


def cleanup_one(session, rid: str, marker: str) -> bool:
    for delay in (0, 1, 2, 4):
        if delay:
            time.sleep(delay)
        current = base._get(session, rid)
        values = current.get("userDefined") or []
        filtered = [
            {k: v for k, v in item.items() if k in {"key", "value"}}
            for item in values
            if not (item.get("key") == MARKER_KEY and item.get("value") == marker)
        ]
        if len(filtered) == len(values):
            return False
        body = {
            "metadata": {
                "sources": [
                    source
                    for source in (current.get("metadata") or {}).get("sources", [])
                    if source.get("type") == "CONTACT"
                ]
            },
            "userDefined": filtered,
        }
        response = session.patch(
            f"{base.BASE}/{rid}:updateContact",
            params={"updatePersonFields": "userDefined"},
            json=body,
            timeout=60,
        )
        if response.status_code < 400:
            return True
        if response.status_code not in RETRYABLE:
            raise RuntimeError(
                f"Marker cleanup failed ({response.status_code}): {response.text[:500]}"
            )
    raise RuntimeError("Marker cleanup remained unavailable after retries")


def cleanup(
    *,
    vcard: Path,
    receipt_path: Path,
    client_secret: Path,
    token_path: Path,
    refreshed_snapshot: Path,
) -> dict[str, int | str]:
    if not receipt_path.exists():
        return {"cleaned": 0, "pending": 0, "refreshed_google_contacts": 0}

    receipt = json.loads(receipt_path.read_text("utf-8"))
    results = receipt.get("results") or {}
    apple = {contact.fingerprint: contact for contact in base.parse_apple_vcard(vcard)}
    session = base._session(client_secret, token_path)

    cleaned = 0
    pending = 0
    for fingerprint, row in results.items():
        if row.get("status") != "success" or row.get("action") != "create":
            continue
        rid = row.get("google_external_id")
        if not isinstance(rid, str) or not rid.startswith("people/"):
            continue
        if fingerprint not in apple:
            raise RuntimeError("Receipt fingerprint no longer maps to vCard")
        try:
            if cleanup_one(session, rid, marker_value(fingerprint)):
                cleaned += 1
        except Exception as exc:
            row["marker_cleanup_error"] = str(exc)[:1000]
            pending += 1
            base.write_json_atomic(receipt_path, receipt)

    receipt["marker_cleanup"] = {"cleaned": cleaned, "pending": pending}
    base.write_json_atomic(receipt_path, receipt)

    contacts, sync = enumerate_saved_contacts(
        client_secret=client_secret,
        token_path=token_path,
        account_scope="google-primary",
    )
    write_snapshot(
        contacts,
        output=refreshed_snapshot,
        account_scope="google-primary",
        next_sync_token=sync,
    )
    return {
        "cleaned": cleaned,
        "pending": pending,
        "refreshed_google_contacts": len(contacts),
        "refreshed_snapshot": str(refreshed_snapshot),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apple-vcard", type=Path, default=Path(".private/people/apple_contacts.vcf"))
    parser.add_argument("--receipt", type=Path, default=Path(".private/people/apple_google_apply_receipt.json"))
    parser.add_argument("--client-secret", type=Path, default=Path(".private/people/google-oauth-client.json"))
    parser.add_argument("--token", type=Path, default=Path(".private/people/google-people-token.json"))
    parser.add_argument("--refreshed-snapshot", type=Path, default=Path(".private/people/google_people_live_after_apple.json"))
    args = parser.parse_args()
    print(
        json.dumps(
            cleanup(
                vcard=args.apple_vcard,
                receipt_path=args.receipt,
                client_secret=args.client_secret,
                token_path=args.token,
                refreshed_snapshot=args.refreshed_snapshot,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
