#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import people_structured_memory_review as base
from repo_env import load_repo_env

DEFAULT_REVIEW = Path('.private/people/structured_memory_review.json')
DEFAULT_RECEIPT = Path('.private/people/profile_relationship_review_receipt.json')
DEFAULT_CANDIDATE_REVIEW = Path('.private/people/obsidian_candidate_review.json')
DEFAULT_MANIFEST = Path('.private/people/obsidian_person_links.json')
DEFAULT_SOURCE_ROOT = Path('20 Areas/People')

RELATION_SECTION_HEADING_RE = re.compile(
    r'^\s*#{0,6}\s*(?:family\s*(?:&|and|/)\s*friends|friends\s*(?:&|and|/)\s*family)\s*:?[\s#]*$',
    re.I,
)
PAREN_REL_RE = re.compile(r'^\s*[-*]?\s*(?P<target>.+?)\s*\(\s*(?P<descriptor>[^()]{1,80})\s*\)\s*$')

RELATION_WORDS = {
    'mother': 'parent', 'mom': 'parent', 'father': 'parent', 'dad': 'parent',
    'sister': 'sibling', 'brother': 'sibling',
    'daughter': 'child', 'son': 'child',
    'wife': 'spouse', 'husband': 'spouse', 'partner': 'partner',
    'grandmother': 'grandparent', 'grandma': 'grandparent',
    'grandfather': 'grandparent', 'grandpa': 'grandparent',
    'aunt': 'aunt_uncle', 'uncle': 'aunt_uncle',
    'niece': 'niece_nephew', 'nephew': 'niece_nephew',
    'cousin': 'cousin',
    'friend': 'friend', 'coworker': 'coworker', 'colleague': 'coworker',
}
RELATION_TOKENS = sorted(RELATION_WORDS, key=len, reverse=True)


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')


def _relation_from_descriptor(descriptor: str) -> str | None:
    lowered = descriptor.lower()
    for token in RELATION_TOKENS:
        if re.search(rf'(?<!\w){re.escape(token)}(?!\w)', lowered):
            return token
    return None


def _wikilink_parts(raw: str) -> tuple[str | None, str | None]:
    match = base.WIKILINK_RE.search(raw)
    if not match:
        return None, None
    target = match.group(1).strip().lstrip('/')
    display = (match.group(2) or Path(target).stem).strip()
    return target, display


def _resolve_target(
    raw: str,
    aliases: dict[str, list[str]],
    source_people: dict[str, str],
    *,
    source_note: str,
) -> tuple[str, str | None, str]:
    link_target, display = _wikilink_parts(raw)
    if link_target:
        exact_candidates = [link_target]
        if not link_target.lower().endswith('.md'):
            exact_candidates.append(link_target + '.md')
        if '/' not in link_target:
            local = (Path(source_note).parent / link_target).as_posix()
            exact_candidates.append(local)
            if not local.lower().endswith('.md'):
                exact_candidates.append(local + '.md')
        for candidate in exact_candidates:
            person_id = source_people.get(candidate)
            if person_id:
                return display or Path(link_target).stem, person_id, 'exact_wikilink'
        name = display or Path(link_target).stem
    else:
        name = base._extract_name_token(raw)

    person_id = base._resolve_alias(name, aliases)
    return name, person_id, 'unique_alias' if person_id else 'unresolved_target'


def _direction(owner_id: str, target_id: str, raw_relation: str) -> tuple[str, str, str]:
    relation = raw_relation.lower()
    canonical = RELATION_WORDS[relation]
    if relation in {
        'mother', 'mom', 'father', 'dad',
        'grandmother', 'grandma', 'grandfather', 'grandpa',
        'aunt', 'uncle', 'daughter', 'son', 'niece', 'nephew',
    }:
        return target_id, owner_id, canonical
    return owner_id, target_id, canonical


def _merge_edge(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
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


def enrich_review(
    *,
    vault_root: Path,
    review_path: Path,
    candidate_review_path: Path,
    manifest_path: Path,
    source_root: Path = DEFAULT_SOURCE_ROOT,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    review = base._load_json(review_path)
    if int(review.get('schema_version') or 0) != 1 or review.get('private_artifact') is not True:
        raise ValueError('structured memory private review schema_version 1 is required')

    candidate_review = base._load_json(candidate_review_path)
    if int(candidate_review.get('schema_version') or 0) < 2:
        raise ValueError('candidate review schema_version >= 2 is required')

    source_people, aliases, ownership = base._identity_index(candidate_review, base._manifest_map(manifest_path))
    existing_edges = review.setdefault('relationship_candidates', [])
    edge_by_key = {base._edge_semantic_key(item): item for item in existing_edges}

    added: list[dict[str, Any]] = []
    files_scanned = lines_scanned = sections_found = 0
    held_unresolved = resolved = self_edges_held = collapsed = 0
    exact_wikilink_resolutions = unique_alias_resolutions = 0
    vault = vault_root.resolve()

    for path in base._source_files(vault_root, (source_root,)):
        rel = path.relative_to(vault).as_posix()
        owner_id = source_people.get(rel) or base._owner_for_path(rel, ownership)
        if not owner_id:
            continue

        files_scanned += 1
        text = path.read_text(encoding='utf-8', errors='replace')
        source_sha = base._sha256(text)
        in_relation_section = False
        section_entries = 0

        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            lines_scanned += 1

            if RELATION_SECTION_HEADING_RE.match(line):
                in_relation_section = True
                section_entries = 0
                sections_found += 1
                continue

            if not in_relation_section:
                continue

            parsed = PAREN_REL_RE.match(line)
            if not parsed:
                if section_entries > 0:
                    in_relation_section = False
                continue

            raw_relation = _relation_from_descriptor(parsed.group('descriptor'))
            if not raw_relation:
                if section_entries > 0:
                    in_relation_section = False
                continue

            section_entries += 1
            target_raw = parsed.group('target').strip()
            target_name, target_id, resolution = _resolve_target(
                target_raw,
                aliases,
                source_people,
                source_note=rel,
            )

            if not target_id:
                held_unresolved += 1
                candidate = base._relationship_candidate(
                    owner_id,
                    None,
                    RELATION_WORDS[raw_relation],
                    rel,
                    line_number,
                    source_sha,
                    line,
                    unresolved_name=target_name,
                )
                candidate['resolution'] = 'unresolved_target'
                candidate['profile_section_resolution'] = resolution
                candidate['profile_raw_relation'] = raw_relation
            elif target_id == owner_id:
                self_edges_held += 1
                continue
            else:
                source_id, directed_target_id, canonical = _direction(owner_id, target_id, raw_relation)
                candidate = base._relationship_candidate(
                    source_id,
                    directed_target_id,
                    canonical,
                    rel,
                    line_number,
                    source_sha,
                    line,
                )
                candidate['profile_section_resolution'] = resolution
                candidate['profile_raw_relation'] = raw_relation
                resolved += 1
                if resolution == 'exact_wikilink':
                    exact_wikilink_resolutions += 1
                elif resolution == 'unique_alias':
                    unique_alias_resolutions += 1

            candidate['supporting_evidence_count'] = 1
            semantic = base._edge_semantic_key(candidate)
            existing = edge_by_key.get(semantic)
            if existing:
                _merge_edge(existing, candidate)
                collapsed += 1
                continue
            edge_by_key[semantic] = candidate
            existing_edges.append(candidate)
            added.append(candidate)

    review.setdefault('policy', {})['profile_relationship_sections_enabled'] = True
    review['policy']['profile_relationship_unresolved_names_stay_private'] = True
    review['policy']['profile_relationship_exact_wikilinks_preferred'] = True

    receipt = {
        'schema_version': 1,
        'files_scanned_with_resolved_owner': files_scanned,
        'lines_scanned': lines_scanned,
        'family_friend_sections_found': sections_found,
        'relationship_candidates_added': len(added),
        'resolved_relationship_candidates_added': resolved,
        'held_unresolved_relationship_candidates_added': held_unresolved,
        'self_edges_held': self_edges_held,
        'collapsed_duplicate_relationship_evidence': collapsed,
        'exact_wikilink_resolutions': exact_wikilink_resolutions,
        'unique_alias_resolutions': unique_alias_resolutions,
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
    return review, receipt, added


def interactive_review(candidates: list[dict[str, Any]]) -> None:
    if not candidates:
        print('\nNo new profile relationship candidates found.')
        return
    print('\nProfile relationship review. No database or Obsidian writes occur here.\n')
    for candidate in candidates:
        if candidate.get('resolution') != 'two_resolved_people':
            continue
        support = int(candidate.get('supporting_evidence_count') or 1)
        support_text = f'; {support} supporting source lines' if support > 1 else ''
        print(f"\nperson_relationship_edge: {candidate['evidence_line']}")
        print(f"  -> relationship: {candidate['relationship_type']}{support_text}")
        candidate['approved'] = input('Approve this structured relationship? [y/N]: ').strip().lower() in {'y', 'yes'}


def main() -> None:
    load_repo_env()
    parser = argparse.ArgumentParser(description='Enrich the private People structured-memory review with profile relationship sections.')
    parser.add_argument('--vault-root', default=os.environ.get('OBSIDIAN_VAULT_PATH'))
    parser.add_argument('--review', default=str(DEFAULT_REVIEW))
    parser.add_argument('--candidate-review', default=str(DEFAULT_CANDIDATE_REVIEW))
    parser.add_argument('--manifest', default=str(DEFAULT_MANIFEST))
    parser.add_argument('--receipt', default=str(DEFAULT_RECEIPT))
    parser.add_argument('--source-root', default=str(DEFAULT_SOURCE_ROOT))
    parser.add_argument('--interactive', action='store_true')
    args = parser.parse_args()

    if not args.vault_root:
        raise SystemExit('OBSIDIAN_VAULT_PATH is required')

    review, receipt, added = enrich_review(
        vault_root=Path(args.vault_root),
        review_path=Path(args.review),
        candidate_review_path=Path(args.candidate_review),
        manifest_path=Path(args.manifest),
        source_root=Path(args.source_root),
    )
    if args.interactive:
        interactive_review(added)
    _write(Path(args.review), review)
    _write(Path(args.receipt), receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print(f'Private enriched review: {args.review}')


if __name__ == '__main__':
    main()
