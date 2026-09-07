#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import unicodedata
import uuid
from pathlib import Path
from typing import Any

from repo_env import load_repo_env

DEFAULT_CANDIDATE_REVIEW = Path('.private/people/obsidian_candidate_review.json')
DEFAULT_MANIFEST = Path('.private/people/obsidian_person_links.json')
DEFAULT_REVIEW = Path('.private/people/structured_memory_review.json')
DEFAULT_RECEIPT = Path('.private/people/structured_memory_review_receipt.json')
DEFAULT_PLAN = Path('.private/people/structured_memory_plan.json')
DEFAULT_PLAN_RECEIPT = Path('.private/people/structured_memory_plan_receipt.json')
DEFAULT_SOURCE_ROOTS = (
    Path('20 Areas/People'),
    Path('00 Inbox/iCloud Calendar Import 2026-06-25'),
    Path('10 Daily/Diary'),
)

MONTHS = {
    'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
    'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
    'aug': 8, 'august': 8, 'sep': 9, 'sept': 9, 'september': 9,
    'oct': 10, 'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12,
}
MONTH_TOKEN = '|'.join(sorted(MONTHS, key=len, reverse=True))
MONTH_DAY_RE = re.compile(rf'\b(?P<month>{MONTH_TOKEN})\.?\s+(?P<day>[0-3]?\d)(?:st|nd|rd|th)?\b', re.I)
DAY_MONTH_RE = re.compile(rf'\b(?P<day>[0-3]?\d)(?:st|nd|rd|th)?\s+(?P<month>{MONTH_TOKEN})\.?\b', re.I)
MONTH_DAY_YEAR_RE = re.compile(
    rf'\b(?P<month>{MONTH_TOKEN})\.?\s+(?P<day>[0-3]?\d)(?:st|nd|rd|th)?(?:,)?\s+(?P<year>\d{{4}})\b', re.I
)
DAY_MONTH_YEAR_RE = re.compile(
    rf'\b(?P<day>[0-3]?\d)(?:st|nd|rd|th)?\s+(?P<month>{MONTH_TOKEN})\.?(?:,)?\s+(?P<year>\d{{4}})\b', re.I
)
ISO_DATE_RE = re.compile(r'\b(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\b')
TIMELINE_RE = re.compile(r'^\s*-?\s*\*\*(?P<date>\d{4}-\d{2}-\d{2})\*\*\s*[—-]\s*(?P<body>.+)$')
BOLD_SUBJECT_RE = re.compile(r'^\s*-?\s*\*\*(?P<name>[^*]+)\*\*\s*[—:-]\s*(?P<body>.+)$')
WIKILINK_RE = re.compile(r'\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]')
VALID_UUID_RE = re.compile(r'^[0-9a-fA-F-]{36}$')

# Sensitive/death language must win over generic words elsewhere on the same line.
DATE_KEYWORDS = (
    ('passed away', 'memorial', 'sensitive'),
    ('passing', 'memorial', 'sensitive'),
    ('died', 'memorial', 'sensitive'),
    ('death', 'memorial', 'sensitive'),
    ('memorial', 'memorial', 'sensitive'),
    ('remembrance', 'memorial', 'sensitive'),
    ('friendship anniversary', 'friendship_anniversary', 'standard'),
    ('relationship anniversary', 'relationship_anniversary', 'standard'),
    ('birthday', 'birthday', 'standard'),
    ('anniversary', 'anniversary', 'standard'),
)
SINGLETON_REVIEW_DATE_TYPES = {'birthday', 'friendship_anniversary', 'relationship_anniversary'}
RELATED_PERSON_DEATH_RE = re.compile(
    r"(?P<owner>[A-Z][A-Za-z0-9 .()\[\]|'’_-]{1,60}?)['’]s\s+"
    r"(?P<relation>mom|mother|dad|father|sister|brother|wife|husband|partner|daughter|son|grandma|grandmother|grandpa|grandfather|aunt|uncle)['’]s\s+"
    r"(?:passing|death)\b",
    re.I,
)

RELATION_WORDS = {
    'mother': 'parent', 'mom': 'parent', 'father': 'parent', 'dad': 'parent',
    'sister': 'sibling', 'brother': 'sibling', 'daughter': 'child', 'son': 'child',
    'wife': 'spouse', 'husband': 'spouse', 'partner': 'partner',
    'grandmother': 'grandparent', 'grandma': 'grandparent',
    'grandfather': 'grandparent', 'grandpa': 'grandparent',
    'aunt': 'aunt_uncle', 'uncle': 'aunt_uncle', 'friend': 'friend',
    'coworker': 'coworker', 'colleague': 'coworker',
}
REL_TOKEN = '|'.join(sorted(RELATION_WORDS, key=len, reverse=True))
STRUCTURED_REL_RE = re.compile(rf'^\s*[-*]?\s*(?P<rel>{REL_TOKEN})\s*[:—-]\s*(?P<target>.+?)\s*$', re.I)
SUBJECT_IS_POSSESSIVE_RE = re.compile(
    rf'(?P<subject>[A-Z][A-Za-z0-9 .()\'’-]{{1,60}}?)\s+is\s+(?P<owner>[A-Z][A-Za-z0-9 .()\'’-]{{1,60}}?)\'s\s+(?P<rel>{REL_TOKEN})\b', re.I
)
POSSESSIVE_IS_SUBJECT_RE = re.compile(
    rf'(?P<owner>[A-Z][A-Za-z0-9 .()\'’-]{{1,60}}?)\'s\s+(?P<rel>{REL_TOKEN})\s+is\s+(?P<subject>[A-Z][A-Za-z0-9 .()\'’-]{{1,60}})', re.I
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError(f'Expected JSON object in {path}')
    return payload


def _valid_uuid(value: Any) -> bool:
    if not value or not VALID_UUID_RE.match(str(value)):
        return False
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


def _norm_name(value: str | None) -> str:
    if not value:
        return ''
    value = unicodedata.normalize('NFKD', value)
    value = ''.join(ch for ch in value if not unicodedata.combining(ch)).lower()
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', value).split())


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _safe_path(vault_root: Path, relative: Path) -> Path:
    vault = vault_root.resolve()
    candidate = (vault / relative).resolve()
    try:
        candidate.relative_to(vault)
    except ValueError as exc:
        raise ValueError(f'source path escapes configured vault: {relative}') from exc
    return candidate


def _manifest_map(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for item in _load_json(path).get('links') or []:
        note_path = str(item.get('note_path') or '').strip()
        person_id = str(item.get('person_id') or '').strip()
        if note_path and _valid_uuid(person_id):
            result[note_path] = person_id
    return result


def _identity_index(candidate_review: dict[str, Any], manifest: dict[str, str]) -> tuple[dict[str, str], dict[str, list[str]], list[tuple[str, str]]]:
    source_people: dict[str, str] = {}
    aliases: dict[str, list[str]] = {}
    ownership: list[tuple[str, str]] = []
    for entry in candidate_review.get('entries') or []:
        ids: set[str] = set()
        existing = str(entry.get('existing_person_id') or '').strip()
        if _valid_uuid(existing):
            ids.add(existing)
        mapping_paths = [str(v) for v in (entry.get('mapping_note_paths') or []) if str(v).strip()]
        ids.update(manifest[p] for p in mapping_paths if p in manifest)
        if len(ids) != 1:
            continue
        person_id = next(iter(ids))
        source_path = str(entry.get('source_path') or '').strip()
        if source_path:
            source_people[source_path] = person_id
            prefix = source_path if not source_path.lower().endswith('.md') else str(Path(source_path).parent)
            ownership.append((prefix.rstrip('/'), person_id))
        for path in mapping_paths:
            source_people[path] = person_id
            ownership.append((str(Path(path).parent).rstrip('/'), person_id))
        for name in entry.get('note_names') or []:
            normalized = _norm_name(str(name))
            if normalized:
                aliases.setdefault(normalized, []).append(person_id)
    for key in list(aliases):
        aliases[key] = sorted(set(aliases[key]))
    return source_people, aliases, sorted(set(ownership), key=lambda item: len(item[0]), reverse=True)


def _resolve_alias(name: str | None, aliases: dict[str, list[str]]) -> str | None:
    if not name:
        return None
    values = aliases.get(_norm_name(name), [])
    return values[0] if len(values) == 1 else None


def _owner_for_path(rel: str, ownership: list[tuple[str, str]]) -> str | None:
    rel = rel.rstrip('/')
    for prefix, person_id in ownership:
        if rel == prefix or rel.startswith(prefix + '/'):
            return person_id
    return None


def _keyword(text: str) -> tuple[str, str, str] | None:
    lowered = text.lower()
    for phrase, date_type, sensitivity in DATE_KEYWORDS:
        if re.search(rf'(?<!\w){re.escape(phrase)}(?!\w)', lowered):
            return phrase, date_type, sensitivity
    return None


def _validated_date(year: int | None, month: int, day: int) -> tuple[int | None, int, int] | None:
    try:
        dt.date(year or 2000, month, day)
    except ValueError:
        return None
    return year, month, day


def _date_from_line(line: str, keyword: str) -> tuple[int | None, int, int] | None:
    # A recurring calendar timeline timestamp is an occurrence, not an origin year.
    timeline = TIMELINE_RE.match(line)
    body = timeline.group('body') if timeline else line

    for regex in (MONTH_DAY_YEAR_RE, DAY_MONTH_YEAR_RE):
        match = regex.search(body)
        if match:
            month = MONTHS[match.group('month').lower().rstrip('.')]
            return _validated_date(int(match.group('year')), month, int(match.group('day')))

    for regex in (MONTH_DAY_RE, DAY_MONTH_RE):
        match = regex.search(body)
        if match:
            month = MONTHS[match.group('month').lower().rstrip('.')]
            return _validated_date(None, month, int(match.group('day')))

    if timeline:
        match = ISO_DATE_RE.search(timeline.group('date'))
        if match:
            return _validated_date(None, int(match.group('month')), int(match.group('day')))

    if keyword in {'memorial', 'remembrance', 'passed away', 'passing', 'died', 'death'}:
        match = ISO_DATE_RE.search(line)
        if match:
            return _validated_date(int(match.group('year')), int(match.group('month')), int(match.group('day')))
    return None


def _subject_from_line(line: str, keyword: str) -> str | None:
    timeline = TIMELINE_RE.match(line)
    if timeline:
        body = timeline.group('body')
    else:
        bold = BOLD_SUBJECT_RE.match(line)
        if bold:
            return bold.group('name').strip()
        body = line
    match = re.search(rf'(?<!\w){re.escape(keyword)}(?!\w)', body, re.I)
    if not match or match.start() <= 0:
        return None
    prefix = body[:match.start()].strip(' -*—:()\t')
    prefix = re.sub(r'^(?:the|a|an)\s+', '', prefix, flags=re.I)
    prefix = re.sub(r'\s+(?:is|has|had|for|date)$', '', prefix, flags=re.I)
    return prefix if 0 < len(prefix.split()) <= 6 else None


def _extract_name_token(raw: str) -> str:
    wikilink = WIKILINK_RE.search(raw)
    if wikilink:
        return (wikilink.group(2) or Path(wikilink.group(1)).stem).strip()
    raw = re.sub(r'[*_`]', '', raw).strip()
    raw = re.split(r'[,;|()]', raw, maxsplit=1)[0].strip()
    return ' '.join(raw.split()[:6])


def _relationship_direction(owner_id: str, target_id: str, raw_relation: str) -> tuple[str, str, str]:
    rel = raw_relation.lower()
    canonical = RELATION_WORDS[rel]
    if rel in {'mother', 'mom', 'father', 'dad', 'grandmother', 'grandma', 'grandfather', 'grandpa', 'aunt', 'uncle', 'daughter', 'son'}:
        return target_id, owner_id, canonical
    return owner_id, target_id, canonical


def _source_files(vault_root: Path, roots: tuple[Path, ...]) -> list[Path]:
    vault = vault_root.resolve()
    result: list[Path] = []
    for root_rel in roots:
        root = _safe_path(vault_root, root_rel)
        if not root.exists():
            continue
        if root.is_file() and root.suffix.lower() == '.md':
            result.append(root)
        else:
            for path in root.rglob('*.md'):
                rel = path.relative_to(vault)
                if not any(part.startswith('.') for part in rel.parts):
                    result.append(path)
    return sorted(set(result))


def _relationship_candidate(source_id: str, target_id: str | None, relationship_type: str, rel: str, line_number: int, source_sha: str, line: str, *, unresolved_name: str | None = None) -> dict[str, Any]:
    return {
        'candidate_type': 'person_relationship_edge',
        'source_person_id': source_id,
        'target_person_id': target_id,
        'relationship_type': relationship_type,
        'unresolved_target_name': unresolved_name,
        'status': 'active' if target_id else 'held_identity_resolution',
        'started_on': None,
        'ended_on': None,
        'sensitivity_class': 'standard',
        'evidence_basis': 'explicit_source_statement',
        'resolution': 'two_resolved_people' if target_id else 'unresolved_target',
        'source_note': rel,
        'source_line_number': line_number,
        'source_sha256': source_sha,
        'evidence_line': line,
        'approved': False,
    }


def _date_semantic_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
    date_type = str(candidate.get('date_type') or '')
    base = (
        candidate.get('person_id'), date_type, candidate.get('label'),
        int(candidate.get('month') or 0), int(candidate.get('day') or 0),
        str(candidate.get('recurrence') or 'annual'), str(candidate.get('sensitivity_class') or 'standard'),
    )
    if date_type in SINGLETON_REVIEW_DATE_TYPES:
        return base
    return base + (candidate.get('year'),)


def _edge_semantic_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
    return (
        candidate.get('source_person_id'), candidate.get('target_person_id'),
        candidate.get('relationship_type'), candidate.get('status'),
        candidate.get('started_on'), candidate.get('ended_on'),
        candidate.get('sensitivity_class'), candidate.get('resolution'),
        candidate.get('unresolved_target_name'),
    )


def _merge_date_candidate(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    evidence = existing.setdefault('supporting_evidence', [])
    if not evidence:
        evidence.append({
            'source_note': existing.get('source_note'),
            'source_line_number': existing.get('source_line_number'),
            'source_sha256': existing.get('source_sha256'),
            'evidence_line': existing.get('evidence_line'),
        })
    evidence.append({
        'source_note': incoming.get('source_note'),
        'source_line_number': incoming.get('source_line_number'),
        'source_sha256': incoming.get('source_sha256'),
        'evidence_line': incoming.get('evidence_line'),
    })
    existing['supporting_evidence_count'] = len(evidence)
    # Prefer a source that explicitly establishes the origin year.
    if existing.get('year') is None and incoming.get('year') is not None:
        for key in ('year', 'source_note', 'source_line_number', 'source_sha256', 'evidence_line', 'resolution'):
            existing[key] = incoming.get(key)


def build_review(*, vault_root: Path, candidate_review_path: Path, manifest_path: Path, roots: tuple[Path, ...]) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate_review = _load_json(candidate_review_path)
    if int(candidate_review.get('schema_version') or 0) < 2:
        raise ValueError('candidate review schema_version >= 2 is required')
    source_people, aliases, ownership = _identity_index(candidate_review, _manifest_map(manifest_path))

    date_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    edge_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    files_scanned = lines_scanned = 0
    held_unresolved_relationships = 0
    held_unresolved_dates = 0
    collapsed_duplicate_date_evidence = 0
    collapsed_duplicate_edge_evidence = 0
    vault = vault_root.resolve()

    for path in _source_files(vault_root, roots):
        files_scanned += 1
        rel = path.relative_to(vault).as_posix()
        owner_id = source_people.get(rel) or _owner_for_path(rel, ownership)
        text = path.read_text(encoding='utf-8', errors='replace')
        source_sha = _sha256(text)

        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            lines_scanned += 1

            key = _keyword(line)
            if key:
                raw_keyword, date_type, sensitivity = key
                parsed = _date_from_line(line, raw_keyword)
                if parsed:
                    year, month, day = parsed
                    related_death = RELATED_PERSON_DEATH_RE.search(line) if sensitivity == 'sensitive' else None
                    subject = None if related_death else _subject_from_line(line, raw_keyword)
                    person_id = None if related_death else (_resolve_alias(subject, aliases) if subject else owner_id)
                    if person_id:
                        resolution = 'unique_alias' if subject else 'source_owner'
                    elif related_death:
                        resolution = 'unresolved_related_person'
                        held_unresolved_dates += 1
                    else:
                        resolution = 'unresolved'
                        held_unresolved_dates += 1

                    candidate = {
                        'candidate_type': 'person_date',
                        'person_id': person_id,
                        'date_type': date_type,
                        'label': None,
                        'year': year,
                        'month': month,
                        'day': day,
                        'recurrence': 'annual',
                        'sensitivity_class': sensitivity,
                        'evidence_basis': 'explicit_source_statement',
                        'resolution': resolution,
                        'source_note': rel,
                        'source_line_number': line_number,
                        'source_sha256': source_sha,
                        'evidence_line': line,
                        'supporting_evidence_count': 1,
                        'approved': False,
                    }
                    semantic = _date_semantic_key(candidate)
                    existing = date_by_key.get(semantic)
                    if existing:
                        _merge_date_candidate(existing, candidate)
                        collapsed_duplicate_date_evidence += 1
                    else:
                        date_by_key[semantic] = candidate

            structured = STRUCTURED_REL_RE.match(line)
            if structured and owner_id:
                raw_relation = structured.group('rel').lower()
                target_name = _extract_name_token(structured.group('target'))
                target_id = _resolve_alias(target_name, aliases)
                if target_id and target_id != owner_id:
                    source_id, target_id, canonical = _relationship_direction(owner_id, target_id, raw_relation)
                    candidate = _relationship_candidate(source_id, target_id, canonical, rel, line_number, source_sha, line)
                elif not target_id:
                    held_unresolved_relationships += 1
                    candidate = _relationship_candidate(owner_id, None, RELATION_WORDS[raw_relation], rel, line_number, source_sha, line, unresolved_name=target_name)
                else:
                    candidate = None
                if candidate:
                    semantic = _edge_semantic_key(candidate)
                    if semantic in edge_by_key:
                        collapsed_duplicate_edge_evidence += 1
                    else:
                        edge_by_key[semantic] = candidate

            for pattern in (SUBJECT_IS_POSSESSIVE_RE, POSSESSIVE_IS_SUBJECT_RE):
                match = pattern.search(line)
                if not match:
                    continue
                subject_id = _resolve_alias(_extract_name_token(match.group('subject')), aliases)
                named_owner_id = _resolve_alias(_extract_name_token(match.group('owner')), aliases)
                if not subject_id or not named_owner_id or subject_id == named_owner_id:
                    held_unresolved_relationships += 1
                    continue
                canonical = RELATION_WORDS[match.group('rel').lower()]
                candidate = _relationship_candidate(subject_id, named_owner_id, canonical, rel, line_number, source_sha, line)
                semantic = _edge_semantic_key(candidate)
                if semantic in edge_by_key:
                    collapsed_duplicate_edge_evidence += 1
                else:
                    edge_by_key[semantic] = candidate

    date_candidates = list(date_by_key.values())
    relationship_candidates = list(edge_by_key.values())
    review = {
        'schema_version': 1,
        'private_artifact': True,
        'auto_apply_allowed': False,
        'source_roots': [str(root) for root in roots],
        'date_candidates': date_candidates,
        'relationship_candidates': relationship_candidates,
        'policy': {
            'raw_evidence_is_private': True,
            'exact_identity_resolution_required_for_relationship_edges': True,
            'name_only_auto_persistence_allowed': False,
            'sensitive_auto_persistence_allowed': False,
            'human_approval_required': True,
            'duplicate_supporting_evidence_collapsed': True,
        },
    }
    receipt = {
        'schema_version': 1,
        'files_scanned': files_scanned,
        'lines_scanned': lines_scanned,
        'resolved_person_sources_available': len(source_people),
        'unique_aliases_available': sum(len(v) == 1 for v in aliases.values()),
        'date_candidates_found': len(date_candidates),
        'standard_date_candidates': sum(c['sensitivity_class'] == 'standard' for c in date_candidates),
        'sensitive_date_candidates': sum(c['sensitivity_class'] == 'sensitive' for c in date_candidates),
        'held_unresolved_date_candidates': held_unresolved_dates,
        'collapsed_duplicate_date_evidence': collapsed_duplicate_date_evidence,
        'relationship_candidates_found': len(relationship_candidates),
        'resolved_relationship_candidates': sum(c.get('resolution') == 'two_resolved_people' for c in relationship_candidates),
        'held_unresolved_relationship_candidates': held_unresolved_relationships,
        'collapsed_duplicate_relationship_evidence': collapsed_duplicate_edge_evidence,
        'neon_writes': 0,
        'obsidian_writes': 0,
        'privacy': {
            'review_file_is_private': True,
            'receipt_contains_names': False,
            'receipt_contains_person_ids': False,
            'receipt_contains_note_paths': False,
            'receipt_contains_raw_evidence': False,
        },
    }
    return review, receipt


def _interactive(review: dict[str, Any]) -> None:
    print('\nStructured People memory review. No database or Obsidian writes occur here.\n')
    for section in ('date_candidates', 'relationship_candidates'):
        for candidate in review.get(section) or []:
            if candidate.get('resolution') in {'unresolved', 'unresolved_target', 'unresolved_related_person'}:
                if candidate.get('sensitivity_class') == 'sensitive':
                    print(f"HOLD sensitive unresolved: {candidate['evidence_line']}")
                continue
            if candidate.get('sensitivity_class') == 'sensitive':
                print(f"HOLD sensitive: {candidate['evidence_line']}")
                continue
            print(f"\n{candidate['candidate_type']}: {candidate['evidence_line']}")
            if candidate['candidate_type'] == 'person_date':
                year = f" year={candidate['year']}" if candidate.get('year') is not None else ''
                support = int(candidate.get('supporting_evidence_count') or 1)
                support_text = f"; {support} supporting source lines" if support > 1 else ''
                print(f"  -> {candidate['date_type']} {candidate['month']:02d}-{candidate['day']:02d}{year}{support_text}")
            else:
                print(f"  -> relationship: {candidate['relationship_type']}")
            candidate['approved'] = input('Approve this structured memory? [y/N]: ').strip().lower() in {'y', 'yes'}


def _validated_date_proposal(item: dict[str, Any]) -> dict[str, Any] | None:
    person_id = str(item.get('person_id') or '')
    if not _valid_uuid(person_id):
        return None
    month, day = int(item.get('month') or 0), int(item.get('day') or 0)
    year = item.get('year')
    if year is not None:
        year = int(year)
    dt.date(year or 2000, month, day)
    sensitivity_class = str(item.get('sensitivity_class') or 'standard')
    if sensitivity_class not in {'standard', 'sensitive'}:
        raise ValueError('invalid date sensitivity_class')
    if item.get('evidence_basis') != 'explicit_source_statement':
        raise ValueError('approved dates require explicit_source_statement')
    date_type = str(item.get('date_type') or '').strip()
    if not date_type:
        raise ValueError('approved date requires date_type')
    return {
        'proposal_type': 'person_date',
        'person_id': person_id,
        'date_type': date_type,
        'label': item.get('label'),
        'year': year,
        'month': month,
        'day': day,
        'recurrence': str(item.get('recurrence') or 'annual'),
        'source_kind': 'user_edited_import',
        'source_system_id': 'obsidian',
        'confidence': 1.0,
        'sensitivity_class': sensitivity_class,
        'source_sha256': str(item.get('source_sha256') or ''),
    }


def _plan_date_key(proposal: dict[str, Any]) -> tuple[Any, ...]:
    date_type = proposal['date_type']
    base = (
        proposal['person_id'], date_type, proposal.get('label'),
        proposal['month'], proposal['day'], proposal['recurrence'], proposal['sensitivity_class'],
    )
    if date_type in SINGLETON_REVIEW_DATE_TYPES:
        return base
    return base + (proposal.get('year'),)


def _plan_edge_key(proposal: dict[str, Any]) -> tuple[Any, ...]:
    return (
        proposal['source_person_id'], proposal['target_person_id'], proposal['relationship_type'],
        proposal['status'], proposal.get('started_on'), proposal.get('ended_on'), proposal['sensitivity_class'],
    )


def validate_reviewed(reviewed_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    reviewed = _load_json(reviewed_path)
    if int(reviewed.get('schema_version') or 0) != 1 or reviewed.get('private_artifact') is not True:
        raise ValueError('structured memory review schema_version 1 private artifact required')

    date_proposals: dict[tuple[Any, ...], dict[str, Any]] = {}
    edge_proposals: dict[tuple[Any, ...], dict[str, Any]] = {}
    sensitive = held = deduped_dates = deduped_edges = 0

    for item in reviewed.get('date_candidates') or []:
        if not bool(item.get('approved')):
            continue
        proposal = _validated_date_proposal(item)
        if proposal is None:
            held += 1
            continue
        sensitive += int(proposal['sensitivity_class'] == 'sensitive')
        semantic = _plan_date_key(proposal)
        existing = date_proposals.get(semantic)
        if existing:
            deduped_dates += 1
            if existing.get('year') is None and proposal.get('year') is not None:
                date_proposals[semantic] = proposal
        else:
            date_proposals[semantic] = proposal

    for item in reviewed.get('relationship_candidates') or []:
        if not bool(item.get('approved')):
            continue
        source_id = str(item.get('source_person_id') or '')
        target_id = str(item.get('target_person_id') or '')
        if not _valid_uuid(source_id) or not _valid_uuid(target_id) or source_id == target_id or item.get('resolution') != 'two_resolved_people':
            held += 1
            continue
        if item.get('evidence_basis') != 'explicit_source_statement':
            raise ValueError('approved relationship edges require explicit_source_statement')
        sensitivity_class = str(item.get('sensitivity_class') or 'standard')
        if sensitivity_class not in {'standard', 'sensitive'}:
            raise ValueError('invalid edge sensitivity_class')
        sensitive += int(sensitivity_class == 'sensitive')
        proposal = {
            'proposal_type': 'person_relationship_edge',
            'source_person_id': source_id,
            'target_person_id': target_id,
            'relationship_type': str(item.get('relationship_type') or '').strip(),
            'status': str(item.get('status') or 'active'),
            'started_on': item.get('started_on'),
            'ended_on': item.get('ended_on'),
            'source_kind': 'user_edited_import',
            'source_system_id': 'obsidian',
            'confidence': 1.0,
            'sensitivity_class': sensitivity_class,
            'source_sha256': str(item.get('source_sha256') or ''),
        }
        semantic = _plan_edge_key(proposal)
        if semantic in edge_proposals:
            deduped_edges += 1
        else:
            edge_proposals[semantic] = proposal

    proposals = list(date_proposals.values()) + list(edge_proposals.values())
    plan = {
        'schema_version': 1,
        'private_artifact': True,
        'apply_allowed': False,
        'proposals': proposals,
        'policy': {
            'requires_separate_apply_authorization': True,
            'raw_evidence_in_plan': False,
            'unresolved_relationship_edges_allowed': False,
            'sensitive_auto_persist_allowed': False,
        },
    }
    receipt = {
        'schema_version': 1,
        'approved_person_dates': len(date_proposals),
        'approved_relationship_edges': len(edge_proposals),
        'approved_sensitive_proposals': sensitive,
        'held_or_unresolved_approved_items': held,
        'deduplicated_approved_person_dates': deduped_dates,
        'deduplicated_approved_relationship_edges': deduped_edges,
        'apply_allowed': False,
        'neon_writes': 0,
        'privacy': {
            'plan_is_private': True,
            'receipt_contains_names': False,
            'receipt_contains_person_ids': False,
            'receipt_contains_note_paths': False,
            'receipt_contains_raw_evidence': False,
        },
    }
    return plan, receipt


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')


def main() -> None:
    load_repo_env()
    parser = argparse.ArgumentParser(description='Build and validate private important-date and person-relationship memory reviews.')
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('build')
    build.add_argument('--vault-root', default=os.environ.get('OBSIDIAN_VAULT_PATH'))
    build.add_argument('--candidate-review', default=str(DEFAULT_CANDIDATE_REVIEW))
    build.add_argument('--manifest', default=str(DEFAULT_MANIFEST))
    build.add_argument('--review', default=str(DEFAULT_REVIEW))
    build.add_argument('--receipt', default=str(DEFAULT_RECEIPT))
    build.add_argument('--interactive', action='store_true')
    build.add_argument('--source-root', action='append', dest='source_roots')
    validate = sub.add_parser('validate')
    validate.add_argument('--reviewed', default=str(DEFAULT_REVIEW))
    validate.add_argument('--plan', default=str(DEFAULT_PLAN))
    validate.add_argument('--receipt', default=str(DEFAULT_PLAN_RECEIPT))
    args = parser.parse_args()

    if args.command == 'build':
        if not args.vault_root:
            raise SystemExit('OBSIDIAN_VAULT_PATH is required')
        roots = tuple(Path(v) for v in args.source_roots) if args.source_roots else DEFAULT_SOURCE_ROOTS
        review, receipt = build_review(
            vault_root=Path(args.vault_root),
            candidate_review_path=Path(args.candidate_review),
            manifest_path=Path(args.manifest),
            roots=roots,
        )
        if args.interactive:
            _interactive(review)
        _write(Path(args.review), review)
        _write(Path(args.receipt), receipt)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        print(f'Private review: {args.review}')
        return

    plan, receipt = validate_reviewed(Path(args.reviewed))
    _write(Path(args.plan), plan)
    _write(Path(args.receipt), receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print(f'Private plan: {args.plan}')


if __name__ == '__main__':
    main()
