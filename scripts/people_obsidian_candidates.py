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
PERSON_ID_KEY = "llm4life_person_id"
ARCHIVE_DIR = "ZZ_Archived"
DIARY_DIR = "Journal Entries"
DIARY_SOURCE_VALUE = "imported_diary_text"

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]")
DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
LEGACY_PERSON_NOTE_NAMES = {
    "about",
    "birthday",
    "contact",
    "dislikes",
    "events",
    "facts",
    "history",
    "interactions",
    "interests",
    "likes",
    "memories",
    "notes",
    "personality",
    "profile",
    "relationship",
    "timeline",
}


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
        lines = text.splitlines()
        heading = next((line[2:].strip() for line in lines if line.startswith("# ")), None)
        return {}, heading
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
    heading = next((line[2:].strip() for line in lines if line.startswith("# ")), None)
    return values, heading


def _unique(values: list[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = value.strip()
        normalized = _norm_name(value)
        if value and normalized and normalized not in seen:
            seen.add(normalized)
            result.append(value)
    return tuple(result)


def _safe_root(vault_root: Path, people_root: Path) -> tuple[Path, Path]:
    root = (vault_root / people_root).resolve()
    vault = vault_root.resolve()
    try:
        root.relative_to(vault)
    except ValueError as exc:
        raise ValueError("people root escapes configured vault") from exc
    if not root.is_dir():
        raise ValueError(f"People root does not exist: {people_root}")
    return vault, root


def _legacy_folder_alias(folder_name: str) -> str:
    return re.sub(r"\s+\d+$", "", folder_name).strip()


def _mapping_paths_in_folder(folder: Path, vault: Path) -> tuple[str, ...]:
    paths: list[str] = []
    for path in sorted(folder.glob("*.md")):
        if path.name.startswith(".") or path.name.startswith("_"):
            continue
        if path.name.lower().endswith("moc.md"):
            continue
        paths.append(path.relative_to(vault).as_posix())
    return tuple(paths)


@dataclass(frozen=True)
class NoteProfile:
    path: str
    names: tuple[str, ...]
    emails: tuple[str, ...]
    phones: tuple[str, ...]
    source_kind: str = "active_profile"
    mapping_note_paths: tuple[str, ...] = ()
    existing_person_id: str | None = None


def _canonical_profiles(vault_root: Path, people_root: Path, *, include_archived: bool) -> list[NoteProfile]:
    vault, root = _safe_root(vault_root, people_root)
    profiles: list[NoteProfile] = []
    for path in root.rglob("00 *.md"):
        rel = path.relative_to(vault)
        if any(part.startswith(".") for part in rel.parts):
            continue
        is_archived = ARCHIVE_DIR in rel.parts
        if is_archived and not include_archived:
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
        raw_names.append(path.parent.name)

        emails: list[str] = []
        phones: list[str] = []
        for key, values in fm.items():
            if key in EMAIL_KEYS:
                emails.extend(value for value in values if _norm_email(value))
            if key in PHONE_KEYS:
                phones.extend(value for value in values if _norm_phone(value))

        ids = [value.strip() for value in fm.get(PERSON_ID_KEY, []) if value.strip()]
        profiles.append(
            NoteProfile(
                path=rel.as_posix(),
                names=_unique(raw_names),
                emails=tuple(sorted(set(emails))),
                phones=tuple(sorted(set(phones))),
                source_kind="archived_profile" if is_archived else "active_profile",
                mapping_note_paths=(rel.as_posix(),),
                existing_person_id=ids[0] if len(set(ids)) == 1 else None,
            )
        )
    return sorted(profiles, key=lambda item: item.path)


def _moc_legacy_aliases(archive_root: Path, vault: Path) -> dict[str, set[str]]:
    aliases: dict[str, set[str]] = {}
    for moc in archive_root.rglob("*.md"):
        if "moc" not in moc.name.lower() and not moc.name.startswith("_"):
            continue
        heading: str | None = None
        for line in moc.read_text(encoding="utf-8").splitlines():
            if line.startswith("### "):
                heading = line[4:].strip()
                heading = re.sub(r"\s*\([^)]*\)\s*$", "", heading).strip()
            for target, label in WIKILINK_RE.findall(line):
                target = target.strip().replace("\\", "/")
                candidates: list[Path] = []
                if target.startswith("20 Areas/People/"):
                    candidates.append((vault / target).resolve())
                else:
                    candidates.append((moc.parent / target).resolve())
                    candidates.append((vault / "20 Areas" / "People" / target).resolve())
                for candidate in candidates:
                    try:
                        rel_to_archive = candidate.relative_to(archive_root.resolve())
                    except ValueError:
                        continue
                    if not rel_to_archive.parts:
                        continue
                    folder = archive_root.joinpath(rel_to_archive.parts[0])
                    if len(rel_to_archive.parts) > 1:
                        target_parent = candidate if candidate.suffix == "" else candidate.parent
                        if target_parent.is_dir():
                            folder = target_parent
                    if folder == archive_root or not folder.exists():
                        continue
                    rel_folder = folder.relative_to(vault).as_posix()
                    if heading:
                        aliases.setdefault(rel_folder, set()).add(heading)
                    if label.strip():
                        aliases.setdefault(rel_folder, set()).add(label.strip())
                    break
    return aliases


def _legacy_archived_profiles(vault_root: Path, people_root: Path) -> list[NoteProfile]:
    vault, root = _safe_root(vault_root, people_root)
    archive_root = root / ARCHIVE_DIR
    if not archive_root.is_dir():
        return []

    canonical_parents = {
        Path(profile.path).parent.as_posix()
        for profile in _canonical_profiles(vault_root, people_root, include_archived=True)
        if profile.source_kind == "archived_profile"
    }
    moc_aliases = _moc_legacy_aliases(archive_root, vault)
    profiles: list[NoteProfile] = []

    for folder in sorted(path for path in archive_root.rglob("*") if path.is_dir()):
        rel_folder = folder.relative_to(vault).as_posix()
        if rel_folder in canonical_parents:
            continue
        mapping_paths = _mapping_paths_in_folder(folder, vault)
        if not mapping_paths:
            continue

        direct_notes = [Path(path).stem.lower() for path in mapping_paths]
        looks_person_like = (
            rel_folder in moc_aliases
            or any(name in LEGACY_PERSON_NOTE_NAMES for name in direct_notes)
            or len(mapping_paths) >= 2
        )
        if not looks_person_like:
            continue

        raw_names = [folder.name, _legacy_folder_alias(folder.name)]
        raw_names.extend(sorted(moc_aliases.get(rel_folder, set())))

        ids: set[str] = set()
        for rel_path in mapping_paths:
            text = (vault / rel_path).read_text(encoding="utf-8")
            fm, _ = _frontmatter(text)
            ids.update(value.strip() for value in fm.get(PERSON_ID_KEY, []) if value.strip())

        profiles.append(
            NoteProfile(
                path=rel_folder,
                names=_unique(raw_names),
                emails=(),
                phones=(),
                source_kind="archived_legacy_folder",
                mapping_note_paths=mapping_paths,
                existing_person_id=next(iter(ids)) if len(ids) == 1 else None,
            )
        )
    return profiles


def _person_sources(vault_root: Path, people_root: Path, *, include_archived: bool) -> list[NoteProfile]:
    profiles = _canonical_profiles(vault_root, people_root, include_archived=include_archived)
    if include_archived:
        profiles.extend(_legacy_archived_profiles(vault_root, people_root))
    dedup: dict[str, NoteProfile] = {}
    for profile in profiles:
        dedup[profile.path] = profile
    return sorted(dedup.values(), key=lambda item: item.path)


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


def _middle_name_compatible(note_name: str, contact_name: str) -> bool:
    note_tokens = note_name.split()
    contact_tokens = contact_name.split()
    if len(note_tokens) < 2 or len(contact_tokens) < 2:
        return False
    if note_tokens[0] != contact_tokens[0] or note_tokens[-1] != contact_tokens[-1]:
        return False
    short, long = (note_tokens, contact_tokens) if len(note_tokens) <= len(contact_tokens) else (contact_tokens, note_tokens)
    return set(short).issubset(set(long))


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
        middle_compatible = any(_middle_name_compatible(name, contact_name) for name in note_names if name and contact_name)

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
        elif middle_compatible:
            mode = "token_name"
            score = 0.92
            evidence.append("same_first_last_middle_name_difference")
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
    return [item[1] for item in scored[:3]]


def _source_alias_index(profiles: list[NoteProfile]) -> tuple[dict[str, list[NoteProfile]], dict[str, NoteProfile]]:
    aliases: dict[str, list[NoteProfile]] = {}
    paths: dict[str, NoteProfile] = {}
    for profile in profiles:
        source_path = profile.path.removesuffix(".md")
        paths[_norm_name(source_path)] = profile
        paths[_norm_name(Path(source_path).name)] = profile
        if profile.source_kind != "archived_legacy_folder":
            paths[_norm_name(Path(source_path).stem.removeprefix("00 ").strip())] = profile
        for name in profile.names:
            normalized = _norm_name(name)
            if normalized:
                aliases.setdefault(normalized, []).append(profile)
    return aliases, paths


def _diary_date(path: Path, fm: dict[str, list[str]]) -> str | None:
    for key in ("date", "created", "created_at"):
        for value in fm.get(key, []):
            match = DATE_RE.search(value)
            if match:
                return match.group(1)
    match = DATE_RE.search(path.stem)
    return match.group(1) if match else None


def _is_diary_note(rel: Path, fm: dict[str, list[str]]) -> bool:
    return DIARY_DIR in rel.parts or DIARY_SOURCE_VALUE in {value.lower() for value in fm.get("source", [])}


def _resolve_wikilink(
    target: str,
    *,
    aliases: dict[str, list[NoteProfile]],
    paths: dict[str, NoteProfile],
) -> tuple[NoteProfile | None, bool]:
    normalized = _norm_name(target.replace("\\", "/").removesuffix(".md"))
    if not normalized:
        return None, False
    if normalized in paths:
        return paths[normalized], False
    basename = _norm_name(Path(target).stem.removeprefix("00 ").strip())
    candidates = aliases.get(basename, [])
    unique_paths = {candidate.path: candidate for candidate in candidates}
    if len(unique_paths) == 1:
        return next(iter(unique_paths.values())), False
    return None, len(unique_paths) > 1


def _diary_evidence(
    vault_root: Path,
    people_root: Path,
    profiles: list[NoteProfile],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    vault, root = _safe_root(vault_root, people_root)
    aliases, paths = _source_alias_index(profiles)

    evidence: list[dict[str, Any]] = []
    counts = {
        "diary_sources_scanned": 0,
        "diary_sources_with_person_evidence": 0,
        "diary_explicit_profile_links": 0,
        "diary_unique_alias_mentions": 0,
        "diary_ambiguous_profile_wikilinks": 0,
        "diary_ambiguous_alias_mentions": 0,
    }

    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(vault)
        if any(part.startswith(".") for part in rel.parts):
            continue
        text = path.read_text(encoding="utf-8")
        fm, _ = _frontmatter(text)
        if not _is_diary_note(rel, fm):
            continue
        counts["diary_sources_scanned"] += 1

        explicit: dict[str, NoteProfile] = {}
        unresolved_links: list[str] = []
        ambiguous_link_count = 0
        for target, _label in WIKILINK_RE.findall(text):
            resolved, ambiguous = _resolve_wikilink(target.strip(), aliases=aliases, paths=paths)
            if resolved:
                explicit[resolved.path] = resolved
            elif ambiguous:
                ambiguous_link_count += 1
            else:
                unresolved_links.append(target.strip())

        normalized_text = f" {_norm_name(text)} "
        mention_profiles: dict[str, NoteProfile] = {}
        ambiguous_mentions = 0
        for alias, matching_profiles in aliases.items():
            if len(alias) < 4:
                continue
            if f" {alias} " not in normalized_text:
                continue
            unique_profiles = {profile.path: profile for profile in matching_profiles}
            if len(unique_profiles) == 1:
                profile = next(iter(unique_profiles.values()))
                if profile.path not in explicit:
                    mention_profiles[profile.path] = profile
            else:
                ambiguous_mentions += 1

        counts["diary_explicit_profile_links"] += len(explicit)
        counts["diary_unique_alias_mentions"] += len(mention_profiles)
        counts["diary_ambiguous_profile_wikilinks"] += ambiguous_link_count
        counts["diary_ambiguous_alias_mentions"] += ambiguous_mentions

        if explicit or mention_profiles or ambiguous_link_count:
            counts["diary_sources_with_person_evidence"] += 1
            evidence.append(
                {
                    "source_note": rel.as_posix(),
                    "source_date": _diary_date(path, fm),
                    "source_kind": "imported_diary_text"
                    if DIARY_SOURCE_VALUE in {value.lower() for value in fm.get("source", [])}
                    else "journal_entry",
                    "explicit_person_sources": [
                        {
                            "person_source_path": profile.path,
                            "person_id": profile.existing_person_id,
                        }
                        for profile in sorted(explicit.values(), key=lambda item: item.path)
                    ],
                    "mention_candidates": [
                        {
                            "person_source_path": profile.path,
                            "person_id": profile.existing_person_id,
                            "resolution": "review_required",
                        }
                        for profile in sorted(mention_profiles.values(), key=lambda item: item.path)
                    ],
                    "ambiguous_profile_wikilinks": ambiguous_link_count,
                    "unresolved_wikilink_count": len(unresolved_links),
                    "fact_extraction_state": "review_required",
                    "raw_narrative_copied": False,
                }
            )
    return evidence, counts


def _manifest_map(manifest_path: Path | None) -> dict[str, str]:
    if not manifest_path or not manifest_path.exists():
        return {}
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for link in payload.get("links") or []:
        note_path = str(link.get("note_path") or "").strip()
        person_id = str(link.get("person_id") or "").strip()
        if note_path and person_id:
            result[note_path] = person_id
    return result


def build_review(
    *,
    vault_root: Path,
    people_root: Path,
    google_snapshot: Path,
    database_url: str | None,
    include_archived: bool = True,
    include_diary_sources: bool = True,
    existing_manifest: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    profiles = _person_sources(vault_root, people_root, include_archived=include_archived)
    scope, contacts = _load_google(google_snapshot)
    external_ids = [str(item.get("external_id") or "") for item in contacts]
    person_map = _resolve_person_ids(database_url, scope=scope, external_ids=external_ids)
    manifest_map = _manifest_map(existing_manifest)

    review_entries: list[dict[str, Any]] = []
    mode_counts = {
        "already_mapped": 0,
        "strong_identifier": 0,
        "exact_name": 0,
        "token_name": 0,
        "fuzzy_name": 0,
        "unresolved": 0,
    }
    source_counts = {
        "active_profile": 0,
        "archived_profile": 0,
        "archived_legacy_folder": 0,
    }
    mapped_source_ids: dict[str, str] = {}

    for profile in profiles:
        source_counts[profile.source_kind] = source_counts.get(profile.source_kind, 0) + 1
        ids = {profile.existing_person_id} if profile.existing_person_id else set()
        ids.update(manifest_map[path] for path in profile.mapping_note_paths if path in manifest_map)
        ids.discard(None)
        existing_person_id = next(iter(ids)) if len(ids) == 1 else None
        existing_mapping_conflict = len(ids) > 1
        if existing_person_id:
            mapped_source_ids[profile.path] = existing_person_id
            best_mode = "already_mapped"
            candidates: list[dict[str, Any]] = []
            decision = "already_mapped"
        else:
            candidates = _candidate_for_profile(profile, contacts, person_map)
            best_mode = candidates[0]["match_mode"] if candidates else "unresolved"
            decision = "pending"
        mode_counts[best_mode] = mode_counts.get(best_mode, 0) + 1
        review_entries.append(
            {
                "source_path": profile.path,
                "source_kind": profile.source_kind,
                "mapping_note_paths": list(profile.mapping_note_paths),
                "note_names": list(profile.names),
                "existing_person_id": existing_person_id,
                "existing_mapping_conflict": existing_mapping_conflict,
                "candidates": candidates,
                "decision": decision,
                "selected_candidate": None,
            }
        )

    effective_profiles = [
        NoteProfile(
            path=profile.path,
            names=profile.names,
            emails=profile.emails,
            phones=profile.phones,
            source_kind=profile.source_kind,
            mapping_note_paths=profile.mapping_note_paths,
            existing_person_id=mapped_source_ids.get(profile.path) or profile.existing_person_id,
        )
        for profile in profiles
    ]
    diary_evidence: list[dict[str, Any]] = []
    diary_counts = {
        "diary_sources_scanned": 0,
        "diary_sources_with_person_evidence": 0,
        "diary_explicit_profile_links": 0,
        "diary_unique_alias_mentions": 0,
        "diary_ambiguous_profile_wikilinks": 0,
        "diary_ambiguous_alias_mentions": 0,
    }
    if include_diary_sources:
        diary_evidence, diary_counts = _diary_evidence(vault_root, people_root, effective_profiles)

    review = {
        "schema_version": 2,
        "vault_scope": os.environ.get("OBSIDIAN_VAULT_SCOPE") or "primary-vault",
        "google_account_scope": scope,
        "auto_apply_allowed": False,
        "entries": review_entries,
        "diary_evidence": diary_evidence,
        "diary_policy": {
            "diary_notes_are_people": False,
            "raw_narrative_copied": False,
            "plain_name_mentions_require_review": True,
            "fact_extraction_requires_review": True,
        },
    }
    receipt = {
        "schema_version": 2,
        "person_sources_scanned": len(profiles),
        "person_source_kinds": source_counts,
        "canonical_person_notes_scanned": source_counts["active_profile"] + source_counts["archived_profile"],
        "legacy_archived_person_folders_scanned": source_counts["archived_legacy_folder"],
        "google_contacts_considered": len(contacts),
        "neon_person_ids_resolved": len(person_map),
        "database_resolution_available": bool(database_url),
        "existing_mappings_reused": mode_counts["already_mapped"],
        "best_candidate_modes": mode_counts,
        **diary_counts,
        "name_based_auto_links_created": 0,
        "diary_fact_auto_writes": 0,
        "frontmatter_writes": 0,
        "neon_writes": 0,
        "privacy": {
            "review_file_is_private": True,
            "receipt_contains_names": False,
            "receipt_contains_person_ids": False,
            "receipt_contains_note_paths": False,
            "receipt_contains_emails": False,
            "receipt_contains_phones": False,
            "receipt_contains_diary_prose": False,
        },
    }
    return review, receipt


def _interactive_approve(review: dict[str, Any], existing_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    existing_manifest = existing_manifest or {}
    by_path: dict[str, str] = {}
    for link in existing_manifest.get("links") or []:
        note_path = str(link.get("note_path") or "").strip()
        person_id = str(link.get("person_id") or "").strip()
        if note_path and person_id:
            by_path[note_path] = person_id

    print("\nInteractive review. No notes or database rows are modified here.\n")
    for entry in review.get("entries") or []:
        if entry.get("decision") == "already_mapped":
            continue
        candidates = entry.get("candidates") or []
        if not candidates:
            print(f"SKIP  {entry['source_path']}  — no candidate")
            continue

        print(f"SOURCE  {entry['source_path']} [{entry['source_kind']}]")
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
        confirm = input(f"Link this person source to {selected['google_display_name']}? [y/N]: ").strip().lower()
        if confirm not in {"y", "yes"}:
            continue
        for note_path in entry.get("mapping_note_paths") or []:
            by_path[note_path] = selected["person_id"]
        entry["decision"] = "accept"
        entry["selected_candidate"] = int(raw) - 1
        print("  Accepted for private manifest only.\n")

    return {
        "vault_scope": review["vault_scope"],
        "links": [
            {"person_id": person_id, "note_path": note_path}
            for note_path, person_id in sorted(by_path.items())
        ],
    }


def main() -> None:
    load_repo_env()
    parser = argparse.ArgumentParser(
        description="Generate and optionally review private People↔Obsidian identity candidates and diary evidence."
    )
    parser.add_argument("--vault-root", default=os.environ.get("OBSIDIAN_VAULT_PATH"))
    parser.add_argument("--people-root", default=str(DEFAULT_PEOPLE_ROOT))
    parser.add_argument("--google-snapshot", default=str(DEFAULT_GOOGLE_SNAPSHOT))
    parser.add_argument("--review", default=str(DEFAULT_REVIEW))
    parser.add_argument("--receipt", default=str(DEFAULT_RECEIPT))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL"))
    parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Deprecated compatibility flag; archived People are included by default.",
    )
    parser.add_argument(
        "--exclude-archived",
        action="store_true",
        help="Exclude ZZ_Archived canonical and legacy person sources.",
    )
    parser.add_argument(
        "--exclude-diary-sources",
        action="store_true",
        help="Skip Journal Entries/imported_diary_text evidence scanning.",
    )
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()

    if not args.vault_root:
        raise SystemExit("OBSIDIAN_VAULT_PATH is required")

    manifest_path = Path(args.manifest)
    review, receipt = build_review(
        vault_root=Path(args.vault_root),
        people_root=Path(args.people_root),
        google_snapshot=Path(args.google_snapshot),
        database_url=args.database_url,
        include_archived=not args.exclude_archived,
        include_diary_sources=not args.exclude_diary_sources,
        existing_manifest=manifest_path,
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
        existing = {}
        if manifest_path.exists():
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = _interactive_approve(review, existing)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Private approved mapping manifest: {manifest_path}")
        print(f"Approved mappings: {len(manifest['links'])}")


if __name__ == "__main__":
    main()
