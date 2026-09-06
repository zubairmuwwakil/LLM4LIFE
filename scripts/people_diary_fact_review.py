#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from repo_env import load_repo_env

DEFAULT_CANDIDATE_REVIEW = Path(".private/people/obsidian_candidate_review.json")
DEFAULT_BATCH = Path(".private/people/diary_fact_review_batch.json")
DEFAULT_BATCH_RECEIPT = Path(".private/people/diary_fact_review_batch_receipt.json")
DEFAULT_REVIEWED = Path(".private/people/diary_fact_reviewed.json")
DEFAULT_PLAN = Path(".private/people/diary_fact_plan.json")
DEFAULT_PLAN_RECEIPT = Path(".private/people/diary_fact_plan_receipt.json")

SENSITIVITY_CLASSES = {"standard", "sensitive"}
PROPOSAL_TYPES = {"fact", "interaction"}


def _safe_file(vault_root: Path, relative_path: str) -> Path:
    vault = vault_root.resolve()
    candidate = (vault / relative_path).resolve()
    try:
        candidate.relative_to(vault)
    except ValueError as exc:
        raise ValueError("diary source path escapes configured vault") from exc
    if not candidate.is_file():
        raise ValueError(f"Diary source does not exist: {relative_path}")
    return candidate


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end == -1:
        return text
    return text[end + 5 :]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _valid_uuid(value: str | None) -> bool:
    if not value:
        return False
    try:
        uuid.UUID(value)
        return True
    except (TypeError, ValueError):
        return False


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _resolved_people(evidence: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    resolved: dict[str, dict[str, str]] = {}
    unresolved: list[dict[str, Any]] = []

    for item in evidence.get("explicit_person_sources") or []:
        person_id = str(item.get("person_id") or "").strip()
        source_path = str(item.get("person_source_path") or "").strip()
        if _valid_uuid(person_id):
            resolved[person_id] = {
                "person_id": person_id,
                "person_source_path": source_path,
                "resolution": "explicit_profile_link",
            }
        else:
            unresolved.append(
                {
                    "person_source_path": source_path,
                    "resolution": "profile_link_missing_person_id",
                }
            )

    for item in evidence.get("mention_candidates") or []:
        person_id = str(item.get("person_id") or "").strip()
        source_path = str(item.get("person_source_path") or "").strip()
        unresolved.append(
            {
                "person_id": person_id if _valid_uuid(person_id) else None,
                "person_source_path": source_path,
                "resolution": "plain_name_review_required",
            }
        )

    return sorted(resolved.values(), key=lambda item: item["person_id"]), unresolved


def build_batch(
    *,
    vault_root: Path,
    candidate_review_path: Path,
    offset: int,
    batch_size: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    review = _load_json(candidate_review_path)
    if int(review.get("schema_version") or 0) < 2:
        raise ValueError("Obsidian candidate review schema_version >= 2 is required")

    diary_evidence = review.get("diary_evidence") or []
    if not isinstance(diary_evidence, list):
        raise ValueError("candidate review diary_evidence must be a list")

    eligible: list[dict[str, Any]] = []
    skipped_without_resolved_people = 0
    for evidence in diary_evidence:
        resolved, unresolved = _resolved_people(evidence)
        if not resolved:
            skipped_without_resolved_people += 1
            continue
        source_note = str(evidence.get("source_note") or "").strip()
        if not source_note:
            continue
        source_path = _safe_file(vault_root, source_note)
        full_text = source_path.read_text(encoding="utf-8")
        narrative = _strip_frontmatter(full_text).strip()
        eligible.append(
            {
                "source_note": source_note,
                "source_date": evidence.get("source_date"),
                "source_kind": evidence.get("source_kind") or "journal_entry",
                "source_sha256": _sha256(full_text),
                "resolved_people": resolved,
                "unresolved_people": unresolved,
                "raw_narrative": narrative,
                "proposals": [],
                "review_state": "pending",
            }
        )

    selected = eligible[offset : offset + batch_size]
    batch = {
        "schema_version": 1,
        "private_artifact": True,
        "source_candidate_review": str(candidate_review_path),
        "offset": offset,
        "batch_size": batch_size,
        "eligible_total": len(eligible),
        "items": selected,
        "proposal_contract": {
            "proposal_types": sorted(PROPOSAL_TYPES),
            "fact": {
                "required": [
                    "proposal_type",
                    "person_id",
                    "fact_key",
                    "value",
                    "sensitivity_class",
                    "evidence_basis",
                    "approved",
                ],
                "evidence_basis_allowed": ["explicit_user_statement"],
            },
            "interaction": {
                "required": [
                    "proposal_type",
                    "person_ids",
                    "interaction_type",
                    "occurred_on",
                    "sensitivity_class",
                    "evidence_basis",
                    "approved",
                ],
                "summary_optional": True,
                "evidence_basis_allowed": ["explicit_user_statement"],
            },
            "rules": [
                "Do not infer traits, diagnoses, motives, sexuality, religion, politics, health state, or relationship status beyond explicit diary text.",
                "Sensitive information may be proposed only for human review; it is never silently persisted.",
                "Plain-name person matches are not eligible until identity is separately approved.",
                "Raw narrative remains private and must not be copied to public receipts or Neon.",
            ],
        },
    }
    receipt = {
        "schema_version": 1,
        "diary_evidence_total": len(diary_evidence),
        "eligible_with_resolved_people": len(eligible),
        "skipped_without_resolved_people": skipped_without_resolved_people,
        "batch_offset": offset,
        "batch_size_requested": batch_size,
        "batch_items_written": len(selected),
        "raw_narrative_in_private_batch": True,
        "neon_writes": 0,
        "obsidian_writes": 0,
        "privacy": {
            "batch_file_is_private": True,
            "receipt_contains_diary_prose": False,
            "receipt_contains_names": False,
            "receipt_contains_person_ids": False,
            "receipt_contains_note_paths": False,
        },
    }
    return batch, receipt


def _validated_person_ids(raw: Any, allowed: set[str]) -> list[str]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("interaction person_ids must be a non-empty list")
    result: list[str] = []
    for value in raw:
        person_id = str(value or "").strip()
        if not _valid_uuid(person_id) or person_id not in allowed:
            raise ValueError("proposal references an unresolved or unknown person_id")
        if person_id not in result:
            result.append(person_id)
    return result


def _validate_fact(proposal: dict[str, Any], *, allowed_people: set[str], source_date: str | None) -> dict[str, Any]:
    person_id = str(proposal.get("person_id") or "").strip()
    if not _valid_uuid(person_id) or person_id not in allowed_people:
        raise ValueError("fact proposal references an unresolved or unknown person_id")
    fact_key = str(proposal.get("fact_key") or "").strip()
    if not fact_key or not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{1,79}", fact_key):
        raise ValueError("fact_key must be a stable lowercase machine key")
    sensitivity = str(proposal.get("sensitivity_class") or "").strip().lower()
    if sensitivity not in SENSITIVITY_CLASSES:
        raise ValueError("invalid sensitivity_class")
    if proposal.get("evidence_basis") != "explicit_user_statement":
        raise ValueError("only explicit_user_statement evidence may be promoted")
    if not bool(proposal.get("approved")):
        raise ValueError("only approved proposals may enter the plan")
    if "value" not in proposal:
        raise ValueError("fact proposal is missing value")
    return {
        "proposal_type": "fact",
        "person_id": person_id,
        "fact_key": fact_key,
        "value": proposal["value"],
        "source_kind": "user_edited_import",
        "source_system_id": "obsidian",
        "asserted_on": source_date,
        "confidence": 1.0,
        "sensitivity_class": sensitivity,
    }


def _validate_interaction(
    proposal: dict[str, Any], *, allowed_people: set[str], source_date: str | None
) -> dict[str, Any]:
    person_ids = _validated_person_ids(proposal.get("person_ids"), allowed_people)
    interaction_type = str(proposal.get("interaction_type") or "").strip()
    if not interaction_type or len(interaction_type) > 80:
        raise ValueError("interaction_type must be non-empty and <= 80 characters")
    occurred_on = str(proposal.get("occurred_on") or source_date or "").strip()
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", occurred_on):
        raise ValueError("interaction occurred_on must be an explicit YYYY-MM-DD date")
    sensitivity = str(proposal.get("sensitivity_class") or "").strip().lower()
    if sensitivity not in SENSITIVITY_CLASSES:
        raise ValueError("invalid sensitivity_class")
    if proposal.get("evidence_basis") != "explicit_user_statement":
        raise ValueError("only explicit_user_statement evidence may be promoted")
    if not bool(proposal.get("approved")):
        raise ValueError("only approved proposals may enter the plan")
    summary = proposal.get("summary")
    if summary is not None:
        summary = str(summary).strip()
        if len(summary) > 280:
            raise ValueError("interaction summary must be <= 280 characters")
    return {
        "proposal_type": "interaction",
        "person_ids": person_ids,
        "interaction_type": interaction_type,
        "occurred_on": occurred_on,
        "summary": summary or None,
        "source_kind": "interaction_import",
        "source_system_id": "obsidian",
        "sensitivity_class": sensitivity,
    }


def validate_reviewed(reviewed_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    reviewed = _load_json(reviewed_path)
    items = reviewed.get("items") or []
    if not isinstance(items, list):
        raise ValueError("reviewed items must be a list")

    planned_items: list[dict[str, Any]] = []
    fact_count = 0
    interaction_count = 0
    sensitive_count = 0
    rejected_or_unapproved = 0

    for item in items:
        source_note = str(item.get("source_note") or "").strip()
        source_sha256 = str(item.get("source_sha256") or "").strip()
        source_date = item.get("source_date")
        allowed_people = {
            str(person.get("person_id") or "").strip()
            for person in (item.get("resolved_people") or [])
            if _valid_uuid(str(person.get("person_id") or "").strip())
        }
        if not source_note or not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
            raise ValueError("reviewed item is missing source provenance")
        if not allowed_people:
            raise ValueError("reviewed item has no resolved people")

        planned: list[dict[str, Any]] = []
        for proposal in item.get("proposals") or []:
            if not bool(proposal.get("approved")):
                rejected_or_unapproved += 1
                continue
            proposal_type = str(proposal.get("proposal_type") or "").strip().lower()
            if proposal_type == "fact":
                validated = _validate_fact(proposal, allowed_people=allowed_people, source_date=source_date)
                fact_count += 1
            elif proposal_type == "interaction":
                validated = _validate_interaction(
                    proposal, allowed_people=allowed_people, source_date=source_date
                )
                interaction_count += 1
            else:
                raise ValueError(f"unsupported proposal_type: {proposal_type}")
            if validated.get("sensitivity_class") == "sensitive":
                sensitive_count += 1
            planned.append(validated)

        if planned:
            planned_items.append(
                {
                    "source_note": source_note,
                    "source_sha256": source_sha256,
                    "source_date": source_date,
                    "proposals": planned,
                }
            )

    plan = {
        "schema_version": 1,
        "private_artifact": True,
        "apply_allowed": False,
        "items": planned_items,
        "policy": {
            "requires_separate_apply_authorization": True,
            "raw_diary_prose_in_plan": False,
            "model_suggestion_source_kind_allowed": False,
            "sensitive_auto_persist_allowed": False,
        },
    }
    receipt = {
        "schema_version": 1,
        "reviewed_items": len(items),
        "planned_items": len(planned_items),
        "approved_fact_proposals": fact_count,
        "approved_interaction_proposals": interaction_count,
        "approved_sensitive_proposals": sensitive_count,
        "rejected_or_unapproved_proposals": rejected_or_unapproved,
        "apply_allowed": False,
        "neon_writes": 0,
        "obsidian_writes": 0,
        "privacy": {
            "plan_file_is_private": True,
            "receipt_contains_diary_prose": False,
            "receipt_contains_names": False,
            "receipt_contains_person_ids": False,
            "receipt_contains_note_paths": False,
        },
    }
    return plan, receipt


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    load_repo_env()
    parser = argparse.ArgumentParser(
        description="Build private diary fact-review batches and validate human-approved fact/interaction plans."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    batch_parser = subparsers.add_parser("batch")
    batch_parser.add_argument("--vault-root", default=os.environ.get("OBSIDIAN_VAULT_PATH"))
    batch_parser.add_argument("--candidate-review", default=str(DEFAULT_CANDIDATE_REVIEW))
    batch_parser.add_argument("--output", default=str(DEFAULT_BATCH))
    batch_parser.add_argument("--receipt", default=str(DEFAULT_BATCH_RECEIPT))
    batch_parser.add_argument("--offset", type=int, default=0)
    batch_parser.add_argument("--batch-size", type=int, default=25)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--reviewed", default=str(DEFAULT_REVIEWED))
    validate_parser.add_argument("--plan", default=str(DEFAULT_PLAN))
    validate_parser.add_argument("--receipt", default=str(DEFAULT_PLAN_RECEIPT))

    args = parser.parse_args()

    if args.command == "batch":
        if not args.vault_root:
            raise SystemExit("OBSIDIAN_VAULT_PATH is required")
        if args.offset < 0 or args.batch_size < 1 or args.batch_size > 100:
            raise SystemExit("offset must be >= 0 and batch-size must be 1..100")
        batch, receipt = build_batch(
            vault_root=Path(args.vault_root),
            candidate_review_path=Path(args.candidate_review),
            offset=args.offset,
            batch_size=args.batch_size,
        )
        _write_json(Path(args.output), batch)
        _write_json(Path(args.receipt), receipt)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        print(f"Private diary review batch: {args.output}")
        return

    plan, receipt = validate_reviewed(Path(args.reviewed))
    _write_json(Path(args.plan), plan)
    _write_json(Path(args.receipt), receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print(f"Private validated plan: {args.plan}")


if __name__ == "__main__":
    main()
