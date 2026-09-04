#!/usr/bin/env python3
"""Private Google People API bridge for LLM4LIFE People Phase 2.

This helper exists because the ChatGPT Google Contacts connector is targeted
search/read only. It acquires the user's explicit Google OAuth consent locally,
enumerates saved contacts with durable ``people/...`` resource names, and writes
a privacy-minimized snapshot under ``.private/people/``.

It does not create, update, merge, or delete contacts. Provider writes happen
only from a separately generated migration plan after stable-ID reconciliation.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTACTS_SCOPE = "https://www.googleapis.com/auth/contacts"
CONNECTIONS_URL = "https://people.googleapis.com/v1/people/me/connections"
PERSON_FIELDS = ",".join(
    [
        "addresses",
        "biographies",
        "birthdays",
        "emailAddresses",
        "events",
        "metadata",
        "names",
        "organizations",
        "phoneNumbers",
        "photos",
        "relations",
        "urls",
        "userDefined",
    ]
)


def _first_display_name(person: dict[str, Any]) -> str | None:
    for name in person.get("names") or []:
        value = (name or {}).get("displayName")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _values(person: dict[str, Any], key: str) -> list[str]:
    result: set[str] = set()
    for item in person.get(key) or []:
        value = (item or {}).get("value")
        if isinstance(value, str) and value.strip():
            result.add(value.strip())
    return sorted(result)


def normalize_person(person: dict[str, Any], *, account_scope: str) -> dict[str, Any]:
    """Return only stable identity + match fields + field-presence booleans."""
    resource_name = person.get("resourceName")
    if not isinstance(resource_name, str) or not resource_name.startswith("people/"):
        raise ValueError("People API contact missing durable people/... resourceName")

    metadata = person.get("metadata") or {}
    deleted = bool(metadata.get("deleted", False))
    return {
        "source": "google_contacts",
        "account_scope": account_scope,
        "external_id": resource_name,
        "external_id_stability": "provider_stable",
        "etag": person.get("etag"),
        "display_name": _first_display_name(person),
        "emails": _values(person, "emailAddresses"),
        "phones": _values(person, "phoneNumbers"),
        "field_presence": {
            "address": bool(person.get("addresses")),
            "birthday": bool(person.get("birthdays")),
            "organization": bool(person.get("organizations")),
            "notes": bool(person.get("biographies")),
            "events": bool(person.get("events")),
            "photos": bool(person.get("photos")),
            "relations": bool(person.get("relations")),
            "urls": bool(person.get("urls")),
            "user_defined": bool(person.get("userDefined")),
        },
        "archived": deleted,
    }


def _load_credentials(client_secret: Path, token_path: Path):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise SystemExit(
            "Missing Google OAuth dependencies. Run: "
            "python -m pip install -r requirements-people-phase2.txt"
        ) from exc

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), [CONTACTS_SCOPE])

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        if not client_secret.exists():
            raise SystemExit(
                f"OAuth client file not found: {client_secret}. "
                "Create a Google OAuth Desktop client with People API enabled and "
                "save its downloaded JSON at this private path."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secret), scopes=[CONTACTS_SCOPE]
        )
        creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json() + "\n", encoding="utf-8")
    return creds


def enumerate_saved_contacts(
    *,
    client_secret: Path,
    token_path: Path,
    account_scope: str,
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        from google.auth.transport.requests import AuthorizedSession
    except ImportError as exc:
        raise SystemExit(
            "Missing Google OAuth dependencies. Run: "
            "python -m pip install -r requirements-people-phase2.txt"
        ) from exc

    creds = _load_credentials(client_secret, token_path)
    session = AuthorizedSession(creds)

    contacts: list[dict[str, Any]] = []
    page_token: str | None = None
    next_sync_token: str | None = None

    while True:
        params: dict[str, Any] = {
            "pageSize": 1000,
            "personFields": PERSON_FIELDS,
            "sources": "READ_SOURCE_TYPE_CONTACT",
            "requestSyncToken": "true",
        }
        if page_token:
            params["pageToken"] = page_token

        response = session.get(CONNECTIONS_URL, params=params, timeout=60)
        if response.status_code >= 400:
            raise RuntimeError(
                f"People API enumeration failed ({response.status_code}): "
                f"{response.text[:1000]}"
            )
        payload = response.json()

        for person in payload.get("connections") or []:
            contacts.append(normalize_person(person, account_scope=account_scope))

        page_token = payload.get("nextPageToken")
        if not page_token:
            next_sync_token = payload.get("nextSyncToken")
            break

    contacts.sort(key=lambda item: item["external_id"])
    return contacts, next_sync_token


def write_snapshot(
    contacts: list[dict[str, Any]],
    *,
    output: Path,
    account_scope: str,
    next_sync_token: str | None,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "source": "google_people_api",
        "account_scope": account_scope,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "next_sync_token": next_sync_token,
        "contacts": contacts,
    }
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    enum = sub.add_parser(
        "enumerate",
        help="open Google OAuth consent and enumerate saved contacts with stable IDs",
    )
    enum.add_argument("--account-scope", default="google-primary")
    enum.add_argument(
        "--client-secret",
        type=Path,
        default=Path(".private/people/google-oauth-client.json"),
    )
    enum.add_argument(
        "--token",
        type=Path,
        default=Path(".private/people/google-people-token.json"),
    )
    enum.add_argument(
        "--output",
        type=Path,
        default=Path(".private/people/google_people_live.json"),
    )

    args = parser.parse_args()
    if args.command == "enumerate":
        contacts, sync_token = enumerate_saved_contacts(
            client_secret=args.client_secret,
            token_path=args.token,
            account_scope=args.account_scope,
        )
        write_snapshot(
            contacts,
            output=args.output,
            account_scope=args.account_scope,
            next_sync_token=sync_token,
        )
        print(
            json.dumps(
                {
                    "contacts": len(contacts),
                    "stable_provider_ids": sum(
                        1 for item in contacts if item["external_id"].startswith("people/")
                    ),
                    "private_output": str(args.output),
                    "sync_token_received": bool(sync_token),
                },
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
