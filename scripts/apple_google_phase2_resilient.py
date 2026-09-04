#!/usr/bin/env python3
"""Resilient Apple -> Google Contacts Phase 2 apply/recovery wrapper.

A failed createContact HTTP response does not prove the contact was not
committed. This module prevents blind create retries from producing duplicates.

Safety invariants:
- no provider delete endpoint is implemented;
- prior private receipts are reused;
- old unmarked 5xx create failures are reconciled before the source snapshot is
  refreshed;
- every new create carries a deterministic temporary userDefined marker;
- marker recovery happens once per run and after transient create failures;
- non-retryable 4xx errors fail immediately;
- transient create retries are sequential and exponentially backed off.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import apple_google_phase2 as base

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


def _marker_from_person(person: dict[str, Any]) -> str | None:
    for item in person.get("userDefined") or []:
        if item.get("key") == MARKER_KEY and isinstance(item.get("value"), str):
            return item["value"]
    return None


def _find_marker_people(session, marker: str) -> list[dict[str, Any]]:
    return [person for person in _list_people(session) if _marker_from_person(person) == marker]


def resilient_create(session, body: dict[str, Any]) -> dict[str, Any]:
    marker = _extract_marker(body)
    if not marker:
        raise RuntimeError("Resilient create requires a deterministic migration marker")

    last_error: Exception | None = None
    for attempt, backoff in enumerate((1, 2, 4, 8), 1):
        try:
            response = session.post(
                f"{base.BASE}/people:createContact",
                params={"personFields": base.FIELDS},
                json=body,
                timeout=60,
            )
        except Exception as exc:
            last_error = exc
            response = None
        else:
            if response.status_code < 400:
                return response.json()
            if response.status_code not in RETRYABLE:
                raise RuntimeError(
                    f"People create failed ({response.status_code}): {response.text[:500]}"
                )
            last_error = RuntimeError(
                f"People create transient failure ({response.status_code}): {response.text[:500]}"
            )

        # Network errors and retryable HTTP failures are ambiguous. Poll for the
        # marker before any new POST because Google may already have committed it.
        for poll_delay in (1, 2, 4):
            time.sleep(poll_delay)
            matches = _find_marker_people(session, marker)
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                raise RuntimeError(
                    "Multiple contacts appeared with one migration marker; refusing retry"
                )
        if attempt < 4:
            time.sleep(backoff)

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
    if not apple.display_name and rich >= 1:
        return True
    return False


def _recover_marked_creates(
    *,
    people: list[dict[str, Any]],
    apple_by_fp: dict[str, base.AppleContact],
    results: dict[str, Any],
    receipt_path: Path,
    receipt: dict[str, Any],
) -> int:
    recovered = 0
    by_marker: dict[str, list[dict[str, Any]]] = {}
    for person in people:
        marker = _marker_from_person(person)
        if marker:
            by_marker.setdefault(marker, []).append(person)

    for fingerprint in apple_by_fp:
        marker = marker_value(fingerprint)
        matches = by_marker.get(marker) or []
        if not matches:
            continue
        if len(matches) > 1:
            raise RuntimeError("Multiple contacts share one migration marker; refusing recovery")
        current = results.get(fingerprint) or {}
        if current.get("status") == "success":
            continue
        rid = matches[0].get("resourceName")
        results[fingerprint] = {
            "status": "success",
            "action": "create",
            "google_external_id": rid,
            "recovered_from_migration_marker": True,
            "field_holds": current.get("field_holds") or [],
            "photo_written": bool(current.get("photo_written", False)),
        }
        recovered += 1
        base.write_json_atomic(receipt_path, receipt)
    return recovered


def recover_prior_ambiguous_creates(
    *,
    vcard: Path,
    snapshot: Path,
    receipt_path: Path,
    client_secret: Path,
    token_path: Path,
) -> dict[str, int]:
    if not receipt_path.exists():
        return {"legacy_errors": 0, "marker_recovered": 0, "legacy_recovered": 0}

    receipt = json.loads(receipt_path.read_text("utf-8"))
    results = receipt.setdefault("results", {})
    apple_by_fp = {contact.fingerprint: contact for contact in base.parse_apple_vcard(vcard)}
    session = base._session(client_secret, token_path)
    live_people = _list_people(session)

    marker_recovered = _recover_marked_creates(
        people=live_people,
        apple_by_fp=apple_by_fp,
        results=results,
        receipt_path=receipt_path,
        receipt=receipt,
    )

    errors = [
        (fingerprint, row)
        for fingerprint, row in results.items()
        if row.get("status") == "error"
        and row.get("action") == "create"
        and "People create failed (5" in str(row.get("error", ""))
    ]
    if not errors:
        return {
            "legacy_errors": 0,
            "marker_recovered": marker_recovered,
            "legacy_recovered": 0,
        }

    snapshot_payload = json.loads(snapshot.read_text("utf-8"))
    baseline_ids = {
        item.get("external_id")
        for item in snapshot_payload.get("contacts") or []
        if isinstance(item.get("external_id"), str)
    }
    confirmed_ids = {
        row.get("google_external_id")
        for row in results.values()
        if row.get("status") == "success"
        and row.get("action") == "create"
        and isinstance(row.get("google_external_id"), str)
    }

    legacy_recovered = 0
    for fingerprint, row in errors:
        apple = apple_by_fp.get(fingerprint)
        if apple is None:
            raise RuntimeError("Legacy 5xx receipt no longer maps to the Apple vCard")

        matches: list[dict[str, Any]] = []
        unaccounted_count = 0
        for delay in (0, 2, 4):
            if delay:
                time.sleep(delay)
            live_people = _list_people(session)
            unaccounted = [
                person
                for person in live_people
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
            legacy_recovered += 1
            base.write_json_atomic(receipt_path, receipt)
            continue
        if len(matches) > 1:
            raise RuntimeError(
                "Legacy 5xx recovery found multiple plausible contacts; refusing retry"
            )
        if unaccounted_count > 0:
            raise RuntimeError(
                "Legacy 5xx recovery found unaccounted new Google contacts but could not prove which one belongs to the failed create. Refusing to retry to avoid a duplicate."
            )
        row["recovery"] = "no_ghost_create_detected_after_repeated_enumeration"
        row["retry_with_marker_after_replan"] = True
        base.write_json_atomic(receipt_path, receipt)

    return {
        "legacy_errors": len(errors),
        "marker_recovered": marker_recovered,
        "legacy_recovered": legacy_recovered,
    }


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
        value = recover_prior_ambiguous_creates(
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
