#!/usr/bin/env python3
"""Resilient Apple -> Google Contacts Phase 2 apply/recovery wrapper.

This module exists specifically to make Google People createContact safe across
transient 5xx/network failures. A failed HTTP response does not prove that a
create was not committed, so blind retries can duplicate contacts.

Safety invariants:
- no provider delete endpoint is implemented;
- existing base migration receipts are reused;
- pre-marker 5xx creates are reconciled against contacts added since the source
  snapshot before the snapshot is refreshed;
- all new creates carry a temporary deterministic userDefined migration marker;
- on transient create failures the marker is searched before any retry;
- successful creates are therefore idempotent across retries and process restarts.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import apple_google_phase2 as base
from google_people_phase2 import enumerate_saved_contacts

RETRYABLE = {429, 500, 502, 503, 504}
MARKER_KEY = "LLM4LIFE migration"
MARKER_PREFIX = "people-phase2:"
CONNECTIONS = f"{base.BASE}/people/me/connections"


def marker_value(fingerprint: str) -> str:
    return MARKER_PREFIX + fingerprint[:40]


def add_marker(body: dict[str, Any], fingerprint: str) -> dict[str, Any]:
    result = dict(body)
    values = [dict(x) for x in result.get("userDefined") or []]
    marker = marker_value(fingerprint)
    if not any(x.get("key") == MARKER_KEY and x.get("value") == marker for x in values):
        values.append({"key": MARKER_KEY, "value": marker})
    result["userDefined"] = values
    return result


def _extract_marker(body: dict[str, Any]) -> str | None:
    for item in body.get("userDefined") or []:
        if item.get("key") == MARKER_KEY and isinstance(item.get("value"), str):
            return item["value"]
    return None


def _list_people(session) -> list[dict[str, Any]]:
    people: list[dict[str, Any]] = []
    token: str | None = None
    while True:
        params = {
            "pageSize": 1000,
            "personFields": base.FIELDS,
            "sources": "READ_SOURCE_TYPE_CONTACT",
        }
        if token:
            params["pageToken"] = token
        response = session.get(CONNECTIONS, params=params, timeout=60)
        if response.status_code >= 400:
            raise RuntimeError(
                f"People enumeration failed ({response.status_code}): {response.text[:500]}"
            )
        payload = response.json()
        people.extend(payload.get("connections") or [])
        token = payload.get("nextPageToken")
        if not token:
            return people


def _marker_matches(person: dict[str, Any], marker: str) -> bool:
    return any(
        item.get("key") == MARKER_KEY and item.get("value") == marker
        for item in person.get("userDefined") or []
    )


def _find_marker_people(session, marker: str) -> list[dict[str, Any]]:
    return [person for person in _list_people(session) if _marker_matches(person, marker)]


def resilient_create(session, body: dict[str, Any]) -> dict[str, Any]:
    marker = _extract_marker(body)
    if not marker:
        raise RuntimeError("Resilient create requires a deterministic migration marker")

    existing = _find_marker_people(session, marker)
    if len(existing) == 1:
        return existing[0]
    if len(existing) > 1:
        raise RuntimeError("Multiple contacts share the same migration marker; refusing retry")

    last_error: Exception | None = None
    for attempt, delay in enumerate((1, 2, 4, 8), 1):
        try:
            response = session.post(
                f"{base.BASE}/people:createContact",
                params={"personFields": base.FIELDS},
                json=body,
                timeout=60,
            )
            if response.status_code < 400:
                return response.json()
            if response.status_code not in RETRYABLE:
                raise RuntimeError(
                    f"People create failed ({response.status_code}): {response.text[:500]}"
                )
            last_error = RuntimeError(
                f"People create transient failure ({response.status_code}): {response.text[:500]}"
            )
        except Exception as exc:
            last_error = exc

        # A transient response is ambiguous: the server may have committed the
        # create. Poll for the deterministic marker before attempting another POST.
        for poll_delay in (1, 2, 4):
            time.sleep(poll_delay)
            matches = _find_marker_people(session, marker)
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                raise RuntimeError(
                    "Multiple contacts appeared with the migration marker after a transient create"
                )
        if attempt < 4:
            time.sleep(delay)

    raise RuntimeError(f"People create remained unavailable after safe retries: {last_error}")


def _normalized_name(person: dict[str, Any]) -> str | None:
    for item in person.get("names") or []:
        value = item.get("displayName") or item.get("unstructuredName")
        if value:
            return base.normalize_name(value)
    return None


def _legacy_match_score(apple: base.AppleContact, person: dict[str, Any]) -> tuple[int, int, bool]:
    apple_emails = {base.normalize_email(x.get("value", "")) for x in apple.emails}
    apple_emails.discard(None)
    google_emails = {base.normalize_email(x.get("value", "")) for x in person.get("emailAddresses") or []}
    google_emails.discard(None)

    apple_phones = {
        value
        for item in apple.phones
        if (value := base.normalize_phone(item.get("value", ""))[0])
    }
    google_phones = {
        value
        for item in person.get("phoneNumbers") or []
        if (value := base.normalize_phone(item.get("value", ""))[0])
    }

    strong = int(bool(apple_emails & google_emails)) + int(bool(apple_phones & google_phones))
    same_name = bool(
        apple.display_name
        and base.normalize_name(apple.display_name) == _normalized_name(person)
    )

    rich = 0
    for field_name, incoming in (
        ("addresses", apple.addresses),
        ("organizations", apple.organizations),
        ("urls", apple.urls),
        ("events", apple.events),
        ("nicknames", apple.nicknames),
        ("userDefined", apple.social_user_defined),
    ):
        if incoming:
            current = person.get(field_name) or []
            incoming_sigs = {base._sig(field_name, x) for x in incoming}
            current_sigs = {base._sig(field_name, x) for x in current}
            if incoming_sigs & current_sigs:
                rich += 1
    if apple.birthday and any(
        base._same_date((x.get("date") or {}), apple.birthday)
        for x in person.get("birthdays") or []
    ):
        rich += 1

    return strong, rich, same_name


def _is_safe_legacy_match(apple: base.AppleContact, person: dict[str, Any]) -> bool:
    strong, rich, same_name = _legacy_match_score(apple, person)
    if strong >= 2:
        return True
    if strong >= 1 and same_name:
        return True
    if same_name and rich >= 1:
        return True
    # For a nameless Apple record, one exact rich field is acceptable only in
    # the already-constrained set of unaccounted contacts added during this run.
    if not apple.display_name and rich >= 1:
        return True
    return False


def recover_legacy_ambiguous_creates(
    *,
    vcard: Path,
    snapshot: Path,
    receipt_path: Path,
    client_secret: Path,
    token_path: Path,
) -> dict[str, int]:
    if not receipt_path.exists():
        return {"legacy_errors": 0, "recovered": 0, "safe_to_replan": 1}

    receipt = json.loads(receipt_path.read_text("utf-8"))
    results = receipt.get("results") or {}
    errors = [
        (fingerprint, row)
        for fingerprint, row in results.items()
        if row.get("status") == "error"
        and row.get("action") == "create"
        and "People create failed (5" in str(row.get("error", ""))
    ]
    if not errors:
        return {"legacy_errors": 0, "recovered": 0, "safe_to_replan": 1}

    snapshot_payload = json.loads(snapshot.read_text("utf-8"))
    snapshot_contacts = snapshot_payload.get("contacts") or []
    baseline_ids = {
        item.get("external_id")
        for item in snapshot_contacts
        if isinstance(item.get("external_id"), str)
    }
    confirmed_ids = {
        row.get("google_external_id")
        for row in results.values()
        if row.get("status") == "success"
        and row.get("action") == "create"
        and isinstance(row.get("google_external_id"), str)
    }
    apple_by_fp = {contact.fingerprint: contact for contact in base.parse_apple_vcard(vcard)}
    session = base._session(client_secret, token_path)
    recovered = 0

    for fingerprint, row in errors:
        apple = apple_by_fp.get(fingerprint)
        if apple is None:
            raise RuntimeError("Legacy 5xx receipt no longer maps to the Apple vCard")

        matches: list[dict[str, Any]] = []
        unaccounted_count = 0
        for delay in (0, 2, 4):
            if delay:
                time.sleep(delay)
            live = _list_people(session)
            unaccounted = [
                person
                for person in live
                if person.get("resourceName") not in baseline_ids
                and person.get("resourceName") not in confirmed_ids
            ]
            unaccounted_count = len(unaccounted)
            matches = [person for person in unaccounted if _is_safe_legacy_match(apple, person)]
            if matches:
                break

        if len(matches) == 1:
            rid = matches[0].get("resourceName")
            results[fingerprint] = {
                "status": "success",
                "action": "create",
                "google_external_id": rid,
                "recovered_after_ambiguous_5xx": True,
                "field_holds": ["legacy_create_response_was_ambiguous"],
                "photo_written": False,
            }
            confirmed_ids.add(rid)
            recovered += 1
            base.write_json_atomic(receipt_path, receipt)
            continue
        if len(matches) > 1:
            raise RuntimeError(
                "Legacy 5xx recovery found multiple plausible created contacts; refusing to retry"
            )
        if unaccounted_count > 0:
            raise RuntimeError(
                "Legacy 5xx recovery found unaccounted new Google contacts but could not prove which one belongs to the failed create. Refusing to retry to avoid a duplicate."
            )
        # No new unaccounted contact is visible after repeated enumeration. The
        # failed create can safely be reconsidered after the wrapper refreshes
        # and replans against current provider state.
        row["recovery"] = "no_ghost_create_detected_after_repeated_enumeration"
        row["retry_with_marker_after_replan"] = True
        base.write_json_atomic(receipt_path, receipt)

    return {"legacy_errors": len(errors), "recovered": recovered, "safe_to_replan": 1}


def install_resilient_create() -> None:
    original_build = base.build_create_payload

    def marked_build(apple: base.AppleContact):
        body, holds = original_build(apple)
        if body:
            body = add_marker(body, apple.fingerprint)
        return body, holds

    base.build_create_payload = marked_build
    base._create = resilient_create


def apply_resilient(args) -> dict[str, Any]:
    install_resilient_create()
    return base.apply_plan(
        args.plan,
        args.apple_vcard,
        args.google_snapshot,
        args.receipt,
        client_secret=args.client_secret,
        token_path=args.token,
        refreshed_snapshot_path=args.refreshed_snapshot,
        apply=args.apply,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    recover = sub.add_parser("recover")
    recover.add_argument("--apple-vcard", type=Path, default=Path(".private/people/apple_contacts.vcf"))
    recover.add_argument("--google-snapshot", type=Path, default=Path(".private/people/google_people_live.json"))
    recover.add_argument("--receipt", type=Path, default=Path(".private/people/apple_google_apply_receipt.json"))
    recover.add_argument("--client-secret", type=Path, default=Path(".private/people/google-oauth-client.json"))
    recover.add_argument("--token", type=Path, default=Path(".private/people/google-people-token.json"))

    apply = sub.add_parser("apply")
    apply.add_argument("--plan", type=Path, default=Path(".private/people/apple_google_plan.json"))
    apply.add_argument("--apple-vcard", type=Path, default=Path(".private/people/apple_contacts.vcf"))
    apply.add_argument("--google-snapshot", type=Path, default=Path(".private/people/google_people_live.json"))
    apply.add_argument("--receipt", type=Path, default=Path(".private/people/apple_google_apply_receipt.json"))
    apply.add_argument("--client-secret", type=Path, default=Path(".private/people/google-oauth-client.json"))
    apply.add_argument("--token", type=Path, default=Path(".private/people/google-people-token.json"))
    apply.add_argument("--refreshed-snapshot", type=Path, default=Path(".private/people/google_people_live_after_apple.json"))
    apply.add_argument("--apply", action="store_true")

    args = parser.parse_args()
    if args.command == "recover":
        value = recover_legacy_ambiguous_creates(
            vcard=args.apple_vcard,
            snapshot=args.google_snapshot,
            receipt_path=args.receipt,
            client_secret=args.client_secret,
            token_path=args.token,
        )
    else:
        value = apply_resilient(args)
    print(json.dumps(value, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
