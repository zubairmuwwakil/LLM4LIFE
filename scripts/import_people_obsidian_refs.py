#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_SYSTEM = "obsidian"
EXPECTED_INTERNAL_TYPE = "person"
EXPECTED_REF_KIND = "narrative"
EXPECTED_LINK_CONTRACT = "obsidian_frontmatter_v1"
ALLOWED_METADATA_KEYS = {"link_contract"}


def _uuid(value: Any, *, field: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"Invalid UUID for {field}") from exc


def load_and_validate_plan(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError("Plan must be a JSON object")
    if raw.get("schema_version") != 1:
        raise ValueError("Unsupported plan schema_version")
    if raw.get("system_id") != EXPECTED_SYSTEM:
        raise ValueError("Plan system_id must be obsidian")
    if raw.get("link_contract") != EXPECTED_LINK_CONTRACT:
        raise ValueError("Unexpected link contract")

    account_scope = str(raw.get("account_scope") or "").strip()
    if not account_scope:
        raise ValueError("Plan account_scope is required")
    refs = raw.get("refs")
    if not isinstance(refs, list):
        raise ValueError("Plan refs must be a list")

    normalized: list[dict[str, Any]] = []
    external_owners: dict[str, str] = {}
    for entry in refs:
        if not isinstance(entry, dict):
            raise ValueError("Each ref must be an object")
        if entry.get("internal_type") != EXPECTED_INTERNAL_TYPE:
            raise ValueError("Only person refs may be imported")
        if entry.get("system_id") != EXPECTED_SYSTEM:
            raise ValueError("Ref system_id must be obsidian")
        if entry.get("account_scope") != account_scope:
            raise ValueError("Ref account_scope must match plan")
        if entry.get("ref_kind") != EXPECTED_REF_KIND:
            raise ValueError("Ref kind must be narrative")

        person_id = _uuid(entry.get("internal_id"), field="internal_id")
        external_id = str(entry.get("external_id") or "")
        if not external_id.startswith("note:"):
            raise ValueError("Obsidian external_id must be note:<uuid>")
        note_id = _uuid(external_id[len("note:") :], field="external_id note UUID")
        external_id = f"note:{note_id}"

        metadata = entry.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise ValueError("Ref metadata must be an object")
        if set(metadata) - ALLOWED_METADATA_KEYS:
            raise ValueError("Ref metadata contains disallowed/private keys")
        if metadata.get("link_contract") != EXPECTED_LINK_CONTRACT:
            raise ValueError("Ref metadata link_contract mismatch")

        prior = external_owners.get(external_id)
        if prior is not None and prior != person_id:
            raise ValueError("One Obsidian note ID cannot map to two People identities")
        external_owners[external_id] = person_id
        normalized.append(
            {
                "internal_type": EXPECTED_INTERNAL_TYPE,
                "internal_id": person_id,
                "system_id": EXPECTED_SYSTEM,
                "account_scope": account_scope,
                "external_id": external_id,
                "ref_kind": EXPECTED_REF_KIND,
                "metadata": {"link_contract": EXPECTED_LINK_CONTRACT},
            }
        )

    return {
        "schema_version": 1,
        "system_id": EXPECTED_SYSTEM,
        "account_scope": account_scope,
        "link_contract": EXPECTED_LINK_CONTRACT,
        "refs": normalized,
    }


def _receipt(*, requested: int, active_people: int, inserted: int, already_present: int, applied: bool) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "applied": applied,
        "refs_requested": requested,
        "active_people_validated": active_people,
        "refs_inserted": inserted,
        "refs_already_present": already_present,
        "conflicts": 0,
        "privacy": {
            "receipt_contains_person_ids": False,
            "receipt_contains_note_ids": False,
            "receipt_contains_note_paths": False,
            "receipt_contains_narrative": False,
            "neon_contains_note_paths": False,
            "neon_contains_narrative": False,
        },
    }


def import_plan(plan: dict[str, Any], *, database_url: str, apply: bool) -> dict[str, Any]:
    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise RuntimeError("Install requirements-people-phase4.txt before importing") from exc

    refs = plan["refs"]
    person_ids = sorted({entry["internal_id"] for entry in refs})
    external_ids = [entry["external_id"] for entry in refs]
    scope = plan["account_scope"]

    with psycopg.connect(database_url) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id::text FROM llm4life.people WHERE status='active' AND id = ANY(%s::uuid[])",
                    (person_ids,),
                )
                active = {row[0] for row in cur.fetchall()}
                missing = sorted(set(person_ids) - active)
                if missing:
                    raise ValueError(f"Plan references {len(missing)} non-active or missing People identities")

                cur.execute(
                    """
                    SELECT external_id, internal_id::text
                    FROM llm4life.external_refs
                    WHERE system_id='obsidian'
                      AND account_scope=%s
                      AND internal_type='person'
                      AND external_id = ANY(%s::text[])
                    """,
                    (scope, external_ids),
                )
                existing = {row[0]: row[1] for row in cur.fetchall()}
                for entry in refs:
                    owner = existing.get(entry["external_id"])
                    if owner is not None and owner != entry["internal_id"]:
                        raise ValueError("Existing Obsidian external ref conflicts with planned person mapping")

                already = sum(1 for entry in refs if existing.get(entry["external_id"]) == entry["internal_id"])
                missing_entries = [entry for entry in refs if entry["external_id"] not in existing]

                if not apply:
                    return _receipt(
                        requested=len(refs),
                        active_people=len(active),
                        inserted=0,
                        already_present=already,
                        applied=False,
                    )

                for entry in missing_entries:
                    cur.execute(
                        """
                        INSERT INTO llm4life.external_refs (
                          internal_type, internal_id, system_id, account_scope,
                          external_id, ref_kind, metadata, first_seen_at, last_seen_at
                        ) VALUES (%s, %s::uuid, %s, %s, %s, %s, %s, now(), now())
                        ON CONFLICT (system_id, account_scope, internal_type, external_id)
                          WHERE external_id IS NOT NULL
                        DO NOTHING
                        """,
                        (
                            entry["internal_type"],
                            entry["internal_id"],
                            entry["system_id"],
                            entry["account_scope"],
                            entry["external_id"],
                            entry["ref_kind"],
                            Jsonb(entry["metadata"]),
                        ),
                    )

                cur.execute(
                    """
                    SELECT external_id, internal_id::text
                    FROM llm4life.external_refs
                    WHERE system_id='obsidian'
                      AND account_scope=%s
                      AND internal_type='person'
                      AND external_id = ANY(%s::text[])
                    """,
                    (scope, external_ids),
                )
                final = {row[0]: row[1] for row in cur.fetchall()}
                for entry in refs:
                    if final.get(entry["external_id"]) != entry["internal_id"]:
                        raise RuntimeError("Post-insert Obsidian ref verification failed")

                inserted = sum(1 for entry in missing_entries if final.get(entry["external_id"]) == entry["internal_id"])
                return _receipt(
                    requested=len(refs),
                    active_people=len(active),
                    inserted=inserted,
                    already_present=already,
                    applied=True,
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import validated private People↔Obsidian note refs into Neon")
    parser.add_argument("--plan", default=".private/people/obsidian_external_refs_plan.json")
    parser.add_argument("--receipt", default=".private/people/obsidian_neon_import_receipt.json")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("Set DATABASE_URL/NEON_DATABASE_URL or pass --database-url")
    plan = load_and_validate_plan(Path(args.plan))
    receipt = import_plan(plan, database_url=args.database_url, apply=args.apply)
    receipt_path = Path(args.receipt)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print(f"Private aggregate receipt: {receipt_path}")


if __name__ == "__main__":
    main()
