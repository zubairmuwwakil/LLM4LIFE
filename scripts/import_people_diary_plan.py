#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_env import load_repo_env

DEFAULT_PLAN = Path(".private/people/diary_fact_plan.json")
DEFAULT_RECEIPT = Path(".private/people/diary_neon_import_receipt.json")
FACT_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL,
    "https://github.com/zubairmuwwakil/LLM4LIFE#obsidian-diary-fact-v1",
)
INTERACTION_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL,
    "https://github.com/zubairmuwwakil/LLM4LIFE#obsidian-diary-interaction-v1",
)
DATE_RE = re.compile(r"20\d{2}-\d{2}-\d{2}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
FACT_KEY_RE = re.compile(r"[a-z0-9][a-z0-9_.-]{1,79}\Z")


@dataclass(frozen=True)
class FactOp:
    id: uuid.UUID
    person_id: uuid.UUID
    fact_key: str
    value: Any
    asserted_on: str | None
    confidence: float | None
    sensitivity_class: str
    source_sha256: str


@dataclass(frozen=True)
class InteractionOp:
    id: uuid.UUID
    interaction_key: str
    person_ids: tuple[uuid.UUID, ...]
    interaction_type: str
    occurred_on: str
    summary: str | None
    sensitivity_class: str
    source_sha256: str


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("plan must be a JSON object")
    return payload


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _valid_uuid(value: Any) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid person UUID in diary plan") from exc


def _fact_id(
    *,
    source_sha256: str,
    source_date: str | None,
    person_id: uuid.UUID,
    fact_key: str,
    value: Any,
) -> uuid.UUID:
    material = "|".join(
        (
            source_sha256,
            source_date or "",
            str(person_id),
            fact_key,
            _canonical_json(value),
        )
    )
    return uuid.uuid5(FACT_NAMESPACE, material)


def _interaction_identity(
    *,
    source_sha256: str,
    occurred_on: str,
    interaction_type: str,
    person_ids: tuple[uuid.UUID, ...],
    summary: str | None,
) -> tuple[uuid.UUID, str]:
    people = ",".join(sorted(str(value) for value in person_ids))
    material = "|".join(
        (source_sha256, occurred_on, interaction_type, people, summary or "")
    )
    interaction_id = uuid.uuid5(INTERACTION_NAMESPACE, material)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return interaction_id, f"obsidian-diary-v1:{digest}"


def normalize_plan(plan: dict[str, Any]) -> tuple[list[FactOp], list[InteractionOp]]:
    if int(plan.get("schema_version") or 0) != 1:
        raise ValueError("unsupported diary plan schema_version")
    if plan.get("private_artifact") is not True:
        raise ValueError("diary plan must be marked private_artifact=true")
    policy = plan.get("policy") or {}
    if policy.get("requires_separate_apply_authorization") is not True:
        raise ValueError("diary plan must retain the separate-authorization gate")
    if policy.get("raw_diary_prose_in_plan") is not False:
        raise ValueError("diary plan must not contain raw narrative")
    if policy.get("model_suggestion_source_kind_allowed") is not False:
        raise ValueError("model suggestions cannot be imported")
    if policy.get("sensitive_auto_persist_allowed") is not False:
        raise ValueError("sensitive auto-persistence must remain disabled")

    facts: list[FactOp] = []
    interactions: list[InteractionOp] = []
    seen_fact_ids: set[uuid.UUID] = set()
    seen_interaction_keys: set[str] = set()

    for item in plan.get("items") or []:
        if not isinstance(item, dict):
            raise ValueError("plan item must be an object")
        source_sha256 = str(item.get("source_sha256") or "").strip().lower()
        if not SHA256_RE.fullmatch(source_sha256):
            raise ValueError("plan item is missing a valid source_sha256")
        source_date_raw = item.get("source_date")
        source_date = str(source_date_raw).strip() if source_date_raw is not None else None
        if source_date and not DATE_RE.fullmatch(source_date):
            raise ValueError("source_date must be YYYY-MM-DD when present")

        for proposal in item.get("proposals") or []:
            if not isinstance(proposal, dict):
                raise ValueError("proposal must be an object")
            proposal_type = str(proposal.get("proposal_type") or "").strip().lower()
            sensitivity = str(proposal.get("sensitivity_class") or "").strip().lower()
            if sensitivity != "standard":
                raise ValueError(
                    "this importer refuses sensitive diary proposals; use a separate reviewed path"
                )
            if str(proposal.get("source_system_id") or "") != "obsidian":
                raise ValueError("diary proposal source_system_id must be obsidian")

            if proposal_type == "fact":
                if str(proposal.get("source_kind") or "") != "user_edited_import":
                    raise ValueError("fact source_kind must be user_edited_import")
                person_id = _valid_uuid(proposal.get("person_id"))
                fact_key = str(proposal.get("fact_key") or "").strip()
                if not FACT_KEY_RE.fullmatch(fact_key):
                    raise ValueError("invalid fact_key")
                if "value" not in proposal:
                    raise ValueError("fact proposal is missing value")
                asserted_raw = proposal.get("asserted_on")
                asserted_on = str(asserted_raw).strip() if asserted_raw is not None else source_date
                if asserted_on and not DATE_RE.fullmatch(asserted_on):
                    raise ValueError("fact asserted_on must be YYYY-MM-DD")
                if source_date and asserted_on and asserted_on != source_date:
                    raise ValueError("fact asserted_on must match the source diary date")
                confidence_raw = proposal.get("confidence")
                confidence = float(confidence_raw) if confidence_raw is not None else None
                if confidence is not None and not 0 <= confidence <= 1:
                    raise ValueError("fact confidence must be between 0 and 1")
                fact_id = _fact_id(
                    source_sha256=source_sha256,
                    source_date=asserted_on,
                    person_id=person_id,
                    fact_key=fact_key,
                    value=proposal["value"],
                )
                if fact_id in seen_fact_ids:
                    raise ValueError("duplicate deterministic fact in diary plan")
                seen_fact_ids.add(fact_id)
                facts.append(
                    FactOp(
                        id=fact_id,
                        person_id=person_id,
                        fact_key=fact_key,
                        value=proposal["value"],
                        asserted_on=asserted_on,
                        confidence=confidence,
                        sensitivity_class=sensitivity,
                        source_sha256=source_sha256,
                    )
                )
                continue

            if proposal_type == "interaction":
                if str(proposal.get("source_kind") or "") != "interaction_import":
                    raise ValueError("interaction source_kind must be interaction_import")
                raw_people = proposal.get("person_ids")
                if not isinstance(raw_people, list) or not raw_people:
                    raise ValueError("interaction person_ids must be a non-empty list")
                person_ids = tuple(
                    sorted({_valid_uuid(value) for value in raw_people}, key=str)
                )
                interaction_type = str(proposal.get("interaction_type") or "").strip()
                if not interaction_type or len(interaction_type) > 80:
                    raise ValueError("invalid interaction_type")
                occurred_on = str(proposal.get("occurred_on") or source_date or "").strip()
                if not DATE_RE.fullmatch(occurred_on):
                    raise ValueError("interaction occurred_on must be YYYY-MM-DD")
                if source_date and occurred_on != source_date:
                    raise ValueError("interaction occurred_on must match the source diary date")
                summary_raw = proposal.get("summary")
                summary = str(summary_raw).strip() if summary_raw is not None else None
                if summary and len(summary) > 280:
                    raise ValueError("interaction summary must be <= 280 characters")
                interaction_id, interaction_key = _interaction_identity(
                    source_sha256=source_sha256,
                    occurred_on=occurred_on,
                    interaction_type=interaction_type,
                    person_ids=person_ids,
                    summary=summary,
                )
                if interaction_key in seen_interaction_keys:
                    raise ValueError("duplicate deterministic interaction in diary plan")
                seen_interaction_keys.add(interaction_key)
                interactions.append(
                    InteractionOp(
                        id=interaction_id,
                        interaction_key=interaction_key,
                        person_ids=person_ids,
                        interaction_type=interaction_type,
                        occurred_on=occurred_on,
                        summary=summary,
                        sensitivity_class=sensitivity,
                        source_sha256=source_sha256,
                    )
                )
                continue

            raise ValueError(f"unsupported proposal_type: {proposal_type}")

    return facts, interactions


def _plan_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _schema_ready(cur: Any) -> None:
    cur.execute(
        """
        SELECT EXISTS (
          SELECT 1
          FROM information_schema.columns
          WHERE table_schema='llm4life'
            AND table_name='person_facts'
            AND column_name='asserted_on'
            AND data_type='date'
        )
        """
    )
    if not bool(cur.fetchone()[0]):
        raise RuntimeError(
            "llm4life.person_facts.asserted_on is missing; apply migration 005 first"
        )
    cur.execute("SELECT EXISTS (SELECT 1 FROM llm4life.systems WHERE id='obsidian')")
    if not bool(cur.fetchone()[0]):
        raise RuntimeError("obsidian system registry row is missing")


def audit_database(cur: Any, facts: list[FactOp], interactions: list[InteractionOp]) -> dict[str, Any]:
    person_ids = sorted(
        {str(op.person_id) for op in facts}
        | {str(person_id) for op in interactions for person_id in op.person_ids}
    )
    active_people: set[str] = set()
    if person_ids:
        cur.execute(
            "SELECT id::text FROM llm4life.people WHERE status='active' AND id = ANY(%s::uuid[])",
            (person_ids,),
        )
        active_people = {row[0] for row in cur.fetchall()}
    missing_people = sorted(set(person_ids) - active_people)

    existing_facts: list[dict[str, Any]] = []
    if person_ids:
        cur.execute(
            """
            SELECT id::text, person_id::text, fact_key, value, asserted_on::text
            FROM llm4life.person_facts
            WHERE person_id = ANY(%s::uuid[])
            """,
            (person_ids,),
        )
        existing_facts = [
            {
                "id": row[0],
                "person_id": row[1],
                "fact_key": row[2],
                "value": row[3],
                "asserted_on": row[4],
            }
            for row in cur.fetchall()
        ]

    existing_fact_ids = {row["id"] for row in existing_facts}
    facts_already_present = 0
    fact_conflicts = 0
    facts_to_insert = 0
    for op in facts:
        if str(op.id) in existing_fact_ids:
            facts_already_present += 1
            continue
        same_slot = [
            row
            for row in existing_facts
            if row["person_id"] == str(op.person_id)
            and row["fact_key"] == op.fact_key
            and row["asserted_on"] == op.asserted_on
        ]
        if same_slot:
            if any(_canonical_json(row["value"]) == _canonical_json(op.value) for row in same_slot):
                facts_already_present += 1
            else:
                fact_conflicts += 1
            continue
        facts_to_insert += 1

    existing_interactions: list[dict[str, Any]] = []
    if person_ids:
        cur.execute(
            """
            SELECT i.id::text,
                   i.interaction_key,
                   i.occurred_on::text,
                   i.interaction_type,
                   i.summary,
                   array_agg(ip.person_id::text ORDER BY ip.person_id::text) AS person_ids
            FROM llm4life.interactions i
            JOIN llm4life.interaction_people ip ON ip.interaction_id=i.id
            WHERE i.id IN (
              SELECT DISTINCT ip2.interaction_id
              FROM llm4life.interaction_people ip2
              WHERE ip2.person_id = ANY(%s::uuid[])
            )
            GROUP BY i.id, i.interaction_key, i.occurred_on, i.interaction_type, i.summary
            """,
            (person_ids,),
        )
        existing_interactions = [
            {
                "id": row[0],
                "interaction_key": row[1],
                "occurred_on": row[2],
                "interaction_type": row[3],
                "summary": row[4],
                "person_ids": tuple(row[5] or []),
            }
            for row in cur.fetchall()
        ]

    existing_keys = {row["interaction_key"] for row in existing_interactions if row["interaction_key"]}
    interactions_already_present = 0
    interaction_conflicts = 0
    interactions_to_insert = 0
    for op in interactions:
        if op.interaction_key in existing_keys:
            interactions_already_present += 1
            continue
        people = tuple(sorted(str(value) for value in op.person_ids))
        same_slot = [
            row
            for row in existing_interactions
            if row["occurred_on"] == op.occurred_on
            and row["interaction_type"] == op.interaction_type
            and tuple(sorted(row["person_ids"])) == people
        ]
        if same_slot:
            if any((row["summary"] or None) == (op.summary or None) for row in same_slot):
                interactions_already_present += 1
            else:
                interaction_conflicts += 1
            continue
        interactions_to_insert += 1

    return {
        "missing_active_people": len(missing_people),
        "facts_planned": len(facts),
        "facts_to_insert": facts_to_insert,
        "facts_already_present": facts_already_present,
        "fact_conflicts": fact_conflicts,
        "interactions_planned": len(interactions),
        "interactions_to_insert": interactions_to_insert,
        "interactions_already_present": interactions_already_present,
        "interaction_conflicts": interaction_conflicts,
    }


def apply_operations(cur: Any, facts: list[FactOp], interactions: list[InteractionOp]) -> tuple[int, int]:
    from psycopg.types.json import Jsonb

    facts_inserted = 0
    interactions_inserted = 0
    for op in facts:
        cur.execute(
            """
            INSERT INTO llm4life.person_facts (
              id, person_id, fact_key, value, source_kind, source_system_id,
              asserted_on, confidence, sensitivity_class
            )
            VALUES (%s,%s,%s,%s,'user_edited_import','obsidian',%s,%s,%s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                op.id,
                op.person_id,
                op.fact_key,
                Jsonb(op.value),
                op.asserted_on,
                op.confidence,
                op.sensitivity_class,
            ),
        )
        facts_inserted += cur.rowcount

    for op in interactions:
        cur.execute(
            """
            INSERT INTO llm4life.interactions (
              id, interaction_key, occurred_on, interaction_type, source_kind,
              source_system_id, summary
            )
            VALUES (%s,%s,%s,%s,'interaction_import','obsidian',%s)
            ON CONFLICT (interaction_key) DO NOTHING
            """,
            (
                op.id,
                op.interaction_key,
                op.occurred_on,
                op.interaction_type,
                op.summary,
            ),
        )
        created = cur.rowcount
        interactions_inserted += created
        cur.execute(
            "SELECT id FROM llm4life.interactions WHERE interaction_key=%s",
            (op.interaction_key,),
        )
        interaction_id = cur.fetchone()[0]
        for person_id in op.person_ids:
            cur.execute(
                """
                INSERT INTO llm4life.interaction_people (interaction_id, person_id, role)
                VALUES (%s,%s,'participant')
                ON CONFLICT DO NOTHING
                """,
                (interaction_id, person_id),
            )

    return facts_inserted, interactions_inserted


def _write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    load_repo_env()
    parser = argparse.ArgumentParser(
        description="Dry-run or import a reviewed Obsidian diary fact/interaction plan into Neon."
    )
    parser.add_argument("--plan", default=str(DEFAULT_PLAN))
    parser.add_argument("--receipt", default=str(DEFAULT_RECEIPT))
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL"),
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--user-authorized",
        action="store_true",
        help="Required with --apply; records that the separate diary-import authorization was explicit.",
    )
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("DATABASE_URL or NEON_DATABASE_URL is required")
    if args.apply and not args.user_authorized:
        raise SystemExit("Refusing --apply without --user-authorized")

    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit("Install requirements-people-phase4.txt first") from exc

    plan_path = Path(args.plan)
    plan = _load_json(plan_path)
    facts, interactions = normalize_plan(plan)

    with psycopg.connect(args.database_url) as conn:
        with conn.cursor() as cur:
            _schema_ready(cur)
            audit = audit_database(cur, facts, interactions)
            blocked = (
                audit["missing_active_people"] > 0
                or audit["fact_conflicts"] > 0
                or audit["interaction_conflicts"] > 0
            )
            facts_inserted = 0
            interactions_inserted = 0
            if args.apply:
                if blocked:
                    conn.rollback()
                else:
                    facts_inserted, interactions_inserted = apply_operations(
                        cur, facts, interactions
                    )
                    conn.commit()
            else:
                conn.rollback()

    receipt = {
        "schema_version": 1,
        "plan_sha256": _plan_sha256(plan_path),
        "apply_requested": bool(args.apply),
        "user_authorized_flag": bool(args.user_authorized),
        "blocked": blocked,
        **audit,
        "facts_inserted": facts_inserted,
        "interactions_inserted": interactions_inserted,
        "privacy": {
            "receipt_contains_names": False,
            "receipt_contains_person_ids": False,
            "receipt_contains_note_paths": False,
            "receipt_contains_diary_prose": False,
            "receipt_contains_fact_values": False,
        },
    }
    _write_receipt(Path(args.receipt), receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if blocked:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
