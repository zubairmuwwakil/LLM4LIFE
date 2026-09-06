#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from repo_env import load_repo_env

DEFAULT_GOOGLE_SNAPSHOT = Path(".private/people/google_people_live_after_apple.json")
DEFAULT_REVIEW = Path(".private/people/obsidian_candidate_review.json")
DEFAULT_RECEIPT = Path(".private/people/obsidian_candidate_receipt.json")
DEFAULT_MANIFEST = Path(".private/people/obsidian_person_links.json")
DEFAULT_PEOPLE_ROOT = Path("20 Areas/People")

EMAIL_KEYS = {"email", "emails", "contact_email", "contact_emails"}
PHONE_KEYS = {"phone", "phones", "contact_phone", "contact_phones"}


def _norm_name(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _norm_email(value: str) -> str:
    return value.strip().lower()


def _norm_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", value or "")
    if len(digits) < 7:
        return ""
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[-10:]
    return digits[-10:] if len(digits) > 10 else digits


def _split_inline_list(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    if not raw:
        return []
    values: list[str] = []
    for item in raw.split(","):
        item = item.strip()
        if len(item) >= 2 and item[0] == item[-1] and item[0] in {'"', "'"}:
            item = item[1:-1]
        if item:
            values.append(item)
    return values


def _frontmatter(text: str) -> tuple[dict[str, list[str]], str | None]:
    if not text.startswith("---\n"):
        return {}, None
    lines = text.splitlines()
    values: dict[str, list[str]] = {}
    idx = 1
    while idx < len(lines):
        line = lines[idx]
        if line == "---":
            break
        match = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*?)\s*$", line)
        if not match:
            idx += 1
            continue
        key, raw = match.groups()
        key = key.lower()
        if raw:
            values.setdefault(key, []).extend(_split_inline_list(raw))
            idx += 1
            continue
        # Support simple YAML list form:
        # aliases:
        #   - Foo
        idx += 1
        while idx < len(lines):
            list_match = re.match(r"^\s*-\s+(.*?)\s*$", lines[idx])
            if not list_match:
                break
            item = list_match.group(1).strip()
            if len(item) >= 2 and item[0] == item[-1] and item[0] in {'"', "'"}:
                item = item[1:-1]
            if item:
                values.setdefault(key, []).append(item)
            idx += 1
    heading = None
    for line in lines:
        if line.startswith("# "):
            heading = line[2:].strip()
            break
    return values, heading


@dataclass(frozen=True)
class NoteProfile:
    path: str
    names: tuple[str, ...]
    emails: tuple[str, ...]
    phones: tuple[str, ...]


def _canonical_profiles(vault_root: Path, people_root: Path, *, include_archived: bool) -> list[NoteProfile]:
    root = (vault_root / people_root).resolve()
    vault = vault_root.resolve()
    try:
        root.relative_to(vault)
    except ValueError as exc:
        raise ValueError("people root escapes configured vault") from exc
    if not root.is_dir():
        raise ValueError(f"People root does not exist: {people_root}")

    profiles: list[NoteProfile] = []
    for path in root.rglob("00 *.md"):
        rel = path.relative_to(vault)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if not include_archived and "ZZ_Archived" in rel.parts:
            continue
        text = path.read_text(encoding="utf-8")
        fm, heading = _frontmatter(text)
        if "person" not in {value.lower() for value in fm.get("type", [])}:
            continue

        raw_names: list[str] = []
        raw_names.extend(fm.get("aliases", []))
        raw_names.extend(fm.get("title", []))
        if heading:
            raw_names.append(heading)
        raw_names.append(path.stem.removeprefix("00 ").strip())
        if path.parent.name:
            raw_names.append(path.parent.name)

        names: list[str] = []
        seen_names: set[str] = set()
        for raw in raw_names:
            normalized = _norm_name(raw)
            if normalized and normalized not in seen_names:
                seen_names.add(normalized)
                names.append(raw.strip())

        emails: list[str] = []
        phones: list[str] = []
        for key, values in fm.items():
            if key in EMAIL_KEYS:
                emails.extend(value for value in values if _norm_email(value))
            if key in PHONE_KEYS:
                phones.extend(value for value in values if _norm_phone(value))

        profiles.append(
            NoteProfile(
                path=rel.as_posix(),
                names=tuple(names),
                emails=tuple(sorted(set(emails))),
                phones=tuple(sorted(set(phones))),
            )
        )
    return sorted(profiles, key=lambda item: item.path)


def _load_google(path: Path) -> tuple[str, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    contacts = payload.get("contacts") or []
    if not isinstance(contacts, list) or not contacts:
        raise ValueError("Google snapshot has no contacts")
    scope = str(payload.get("account_scope") or "google-primary")
    return scope, contacts


def _resolve_person_ids(database_url: str | None, *, scope: str, external_ids: list[str]) -> dict[str, str]:
    if not database_url:
        return {}
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Install requirements-people-phase4.txt to resolve Neon person IDs") from exc

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT er.external_id, er.internal_id::text
                FROM llm4life.external_refs er
                JOIN llm4life.people p ON p.id = er.internal_id
                WHERE er.system_id='google_contacts'
                  AND er.account_scope=%s
                  AND er.internal_type='person'
                  AND er.archived_at IS NULL
                  AND p.status='active'
                  AND er.external_id = ANY(%s::text[])
                """,
                (scope, external_ids),
            )
            return {row[0]: row[1] for row in cur.fetchall()}


def _candidate_for_profile(profile: NoteProfile, contacts: list[dict[str, Any]], person_map: dict[str, str]) -> list[dict[str, Any]]:
    note_emails = {_norm_email(value) for value in profile.emails if _norm_email(value)}
    note_phones = {_norm_phone(value) for value in profile.phones if _norm_phone(value)}
    note_names = {_norm_name(value) for value in profile.names if _norm_name(value)}

    scored: list[tuple[float, dict[str, Any]]] = []
    for contact in contacts:
        external_id = str(contact.get("external_id") or "")
        display_name = str(contact.get("display_name") or "").strip()
        if not external_id.startswith("people/") or not display_name:
            continue

        contact_emails = {_norm_email(str(v)) for v in (contact.get("emails") or []) if _norm_email(str(v))}
        contact_phones = {_norm_phone(str(v)) for v in (contact.get("phones") or []) if _norm_phone(str(v))}
        contact_name = _norm_name(display_name)

        email_overlap = sorted(note_emails & contact_emails)
        phone_overlap = sorted(note_phones & contact_phones)
        exact_name = bool(contact_name and contact_name in note_names)

        mode = "none"
        score = 0.0
        evidence: list[str] = []
        if email_overlap or phone_overlap:
            mode = "strong_identifier"
            score = 1.0
            if email_overlap:
                evidence.append("exact_email")
            if phone_overlap:
                evidence.append("exact_phone")
        elif exact_name:
            mode = "exact_name"
            score = 0.95
            evidence.append("exact_normalized_name")
        else:
            best_ratio = max((SequenceMatcher(None, name, contact_name).ratio() for name in note_names), default=0.0)
            if best_ratio >= 0.88:
                mode = "fuzzy_name"
                score = round(best_ratio, 4)
                evidence.append("name_similarity")

        if mode == "none":
            continue
        scored.append(
            (
                score,
                {
                    "google_external_id": external_id,
                    "google_display_name": display_name,
                    "person_id": person_map.get(external_id),
                    "match_mode": mode,
                    "score": score,
                    "evidence": evidence,
                },
            )
        )

    scored.sort(key=lambda item: (-item[0], item[1]["google_display_name"].lower(), item[1]["google_external_id"]))
    # Keep review surface small. Strong/exact matches should normally dominate; fuzzy gets top alternatives only.
    return [item[1] for item in scored[:3]]


def build_review(
    *,
    vault_root: Path,
    people_root: Path,
    google_snapshot: Path,
    database_url: str | None,
    include_archived: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    profiles = _canonical_profiles(vault_root, people_root, include_archived=include_archived)
    scope, contacts = _load_google(google_snapshot)
    external_ids = [str(item.get("external_id") or "") for item in contacts]
    person_map = _resolve_person_ids(database_url, scope=scope, external_ids=external_ids)

    review_entries: list[dict[str, Any]] = []
    mode_counts = {"strong_identifier": 0, "exact_name": 0, "fuzzy_name": 0, "unresolved": 0}
    for profile in profiles:
        candidates = _candidate_for_profile(profile, contacts, person_map)
        best_mode = candidates[0]["match_mode"] if candidates else "unresolved"
        mode_counts[best_mode] = mode_counts.get(best_mode, 0) + 1
        review_entries.append(
            {
                "note_path": profile.path,
                "note_names": list(profile.names),
                "candidates": candidates,
                "decision": "pending",
                "selected_candidate": None,
            }
        )

    review = {
        "schema_version": 1,
        "vault_scope": os.environ.get("OBSIDIAN_VAULT_SCOPE") or "primary-vault",
        "google_account_scope": scope,
        "auto_apply_allowed": False,
        "entries": review_entries,
    }
    receipt = {
        "schema_version": 1,
        "canonical_person_notes_scanned": len(profiles),
        "google_contacts_considered": len(contacts),
        "neon_person_ids_resolved": len(person_map),
        "database_resolution_available": bool(database_url),
        "best_candidate_modes": mode_counts,
        "name_based_auto_links_created": 0,
        "frontmatter_writes": 0,
        "neon_writes": 0,
        "privacy": {
            "review_file_is_private": True,
            "receipt_contains_names": False,
            "receipt_contains_person_ids": False,
            "receipt_contains_note_paths": False,
            "receipt_contains_emails": False,
            "receipt_contains_phones": False,
        },
    }
    return review, receipt


def _interactive_approve(review: dict[str, Any]) -> dict[str, Any]:
    accepted: list[dict[str, str]] = []
    print("\nInteractive review. No notes or database rows are modified here.\n")
    for entry in review.get("entries") or []:
        candidates = entry.get("candidates") or []
        if not candidates:
            print(f"SKIP  {entry['note_path']}  — no candidate")
            continue

        print(f"NOTE  {entry['note_path']}")
        for idx, candidate in enumerate(candidates, start=1):
            resolved = "resolved" if candidate.get("person_id") else "NO person_id"
            print(
                f"  {idx}. {candidate['google_display_name']} "
                f"[{candidate['match_mode']} {candidate['score']:.2f}; {resolved}]"
            )
        raw = input("Choose candidate number, or Enter to skip: ").strip()
        if not raw:
            continue
        if not raw.isdigit() or not (1 <= int(raw) <= len(candidates)):
            print("  Invalid choice; skipped.")
            continue
        selected = candidates[int(raw) - 1]
        if not selected.get("person_id"):
            print("  Cannot accept: Neon person_id was not resolved. Configure DATABASE_URL and rerun.")
            continue
        confirm = input(f"Link this canonical note to {selected['google_display_name']}? [y/N]: ").strip().lower()
        if confirm not in {"y", "yes"}:
            continue
        accepted.append({"person_id": selected["person_id"], "note_path": entry["note_path"]})
        entry["decision"] = "accept"
        entry["selected_candidate"] = int(raw) - 1
        print("  Accepted for private manifest only.\n")

    return {"vault_scope": review["vault_scope"], "links": accepted}


def main() -> None:
    load_repo_env()
    parser = argparse.ArgumentParser(
        description="Generate and optionally interactively review private People↔Obsidian identity candidates."
    )
    parser.add_argument("--vault-root", default=os.environ.get("OBSIDIAN_VAULT_PATH"))
    parser.add_argument("--people-root", default=str(DEFAULT_PEOPLE_ROOT))
    parser.add_argument("--google-snapshot", default=str(DEFAULT_GOOGLE_SNAPSHOT))
    parser.add_argument("--review", default=str(DEFAULT_REVIEW))
    parser.add_argument("--receipt", default=str(DEFAULT_RECEIPT))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL"))
    parser.add_argument("--include-archived", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()

    if not args.vault_root:
        raise SystemExit("OBSIDIAN_VAULT_PATH is required")

    review, receipt = build_review(
        vault_root=Path(args.vault_root),
        people_root=Path(args.people_root),
        google_snapshot=Path(args.google_snapshot),
        database_url=args.database_url,
        include_archived=args.include_archived,
    )

    review_path = Path(args.review)
    receipt_path = Path(args.receipt)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps(review, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print(f"Private review file: {review_path}")

    if args.interactive:
        manifest = _interactive_approve(review)
        manifest_path = Path(args.manifest)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Private approved mapping manifest: {manifest_path}")
        print(f"Approved mappings: {len(manifest['links'])}")


if __name__ == "__main__":
    main()
