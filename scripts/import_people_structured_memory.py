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

DEFAULT_PLAN = Path('.private/people/structured_memory_plan.json')
DEFAULT_RECEIPT = Path('.private/people/structured_memory_neon_import_receipt.json')
DATE_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, 'https://github.com/zubairmuwwakil/LLM4LIFE#person-date-v1')
EDGE_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, 'https://github.com/zubairmuwwakil/LLM4LIFE#person-relationship-edge-v1')
SHA_RE = re.compile(r'^[0-9a-f]{64}$')
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
SINGLETON_DATE_TYPES = {'birthday', 'friendship_anniversary', 'relationship_anniversary'}


@dataclass(frozen=True)
class DateOp:
    id: uuid.UUID
    person_id: uuid.UUID
    date_type: str
    label: str | None
    year: int | None
    month: int
    day: int
    recurrence: str
    source_kind: str
    source_system_id: str
    confidence: float | None
    sensitivity_class: str
    source_sha256: str


@dataclass(frozen=True)
class EdgeOp:
    id: uuid.UUID
    source_person_id: uuid.UUID
    target_person_id: uuid.UUID
    relationship_type: str
    status: str
    started_on: str | None
    ended_on: str | None
    source_kind: str
    source_system_id: str
    confidence: float | None
    sensitivity_class: str
    source_sha256: str


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('structured memory plan must be a JSON object')
    return payload


def _uuid(value: Any) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError('invalid People UUID in structured memory plan') from exc


def _confidence(value: Any) -> float | None:
    if value is None:
        return None
    result = float(value)
    if not 0 <= result <= 1:
        raise ValueError('confidence must be between 0 and 1')
    return result


def _source_sha(value: Any) -> str:
    result = str(value or '').lower().strip()
    if not SHA_RE.fullmatch(result):
        raise ValueError('structured memory proposal requires source_sha256')
    return result


def _date_id(op: dict[str, Any], person_id: uuid.UUID, source_sha: str) -> uuid.UUID:
    material = '|'.join([
        source_sha, str(person_id), str(op['date_type']), str(op.get('label') or ''),
        str(op.get('year') or ''), str(op['month']), str(op['day']), str(op['recurrence']),
    ])
    return uuid.uuid5(DATE_NAMESPACE, material)


def _edge_id(op: dict[str, Any], source_id: uuid.UUID, target_id: uuid.UUID, source_sha: str) -> uuid.UUID:
    material = '|'.join([
        source_sha, str(source_id), str(target_id), str(op['relationship_type']),
        str(op.get('status') or 'active'), str(op.get('started_on') or ''), str(op.get('ended_on') or ''),
    ])
    return uuid.uuid5(EDGE_NAMESPACE, material)


def normalize_plan(plan: dict[str, Any]) -> tuple[list[DateOp], list[EdgeOp]]:
    if int(plan.get('schema_version') or 0) != 1 or plan.get('private_artifact') is not True:
        raise ValueError('structured memory plan schema_version 1 private artifact required')
    policy = plan.get('policy') or {}
    if policy.get('requires_separate_apply_authorization') is not True:
        raise ValueError('structured memory plan must preserve separate apply authorization')
    if policy.get('raw_evidence_in_plan') is not False:
        raise ValueError('raw evidence may not enter the import plan')
    if policy.get('unresolved_relationship_edges_allowed') is not False:
        raise ValueError('unresolved relationship edges may not enter the plan')
    if policy.get('sensitive_auto_persist_allowed') is not False:
        raise ValueError('sensitive auto-persistence must remain disabled')

    dates: list[DateOp] = []
    edges: list[EdgeOp] = []
    seen_ids: set[uuid.UUID] = set()

    for proposal in plan.get('proposals') or []:
        if not isinstance(proposal, dict):
            raise ValueError('proposal must be an object')
        proposal_type = str(proposal.get('proposal_type') or '')
        sensitivity = str(proposal.get('sensitivity_class') or 'standard')
        if sensitivity != 'standard':
            raise ValueError('routine structured-memory importer refuses sensitive proposals')
        if str(proposal.get('source_system_id') or '') != 'obsidian':
            raise ValueError('structured memory source_system_id must be obsidian')
        if str(proposal.get('source_kind') or '') != 'user_edited_import':
            raise ValueError('structured memory source_kind must be user_edited_import')
        source_sha = _source_sha(proposal.get('source_sha256'))
        confidence = _confidence(proposal.get('confidence'))

        if proposal_type == 'person_date':
            person_id = _uuid(proposal.get('person_id'))
            date_type = str(proposal.get('date_type') or '').strip()
            if not date_type or len(date_type) > 80:
                raise ValueError('invalid date_type')
            label_raw = proposal.get('label')
            label = str(label_raw).strip() if label_raw is not None else None
            if label == '':
                label = None
            year_raw = proposal.get('year')
            year = int(year_raw) if year_raw is not None else None
            month, day = int(proposal.get('month') or 0), int(proposal.get('day') or 0)
            import datetime as _dt
            _dt.date(year or 2000, month, day)
            recurrence = str(proposal.get('recurrence') or 'annual')
            if recurrence not in {'annual', 'none'}:
                raise ValueError('invalid recurrence')
            op_id = _date_id(proposal, person_id, source_sha)
            if op_id in seen_ids:
                raise ValueError('duplicate deterministic structured memory proposal')
            seen_ids.add(op_id)
            dates.append(DateOp(
                id=op_id, person_id=person_id, date_type=date_type, label=label, year=year,
                month=month, day=day, recurrence=recurrence, source_kind='user_edited_import',
                source_system_id='obsidian', confidence=confidence, sensitivity_class=sensitivity,
                source_sha256=source_sha,
            ))
            continue

        if proposal_type == 'person_relationship_edge':
            source_id = _uuid(proposal.get('source_person_id'))
            target_id = _uuid(proposal.get('target_person_id'))
            if source_id == target_id:
                raise ValueError('person relationship self-edge is not allowed')
            relationship_type = str(proposal.get('relationship_type') or '').strip()
            if not relationship_type or len(relationship_type) > 80:
                raise ValueError('invalid relationship_type')
            status = str(proposal.get('status') or 'active')
            if status not in {'active', 'historical', 'unknown', 'retracted'}:
                raise ValueError('invalid relationship status')
            started = proposal.get('started_on')
            ended = proposal.get('ended_on')
            started_on = str(started).strip() if started else None
            ended_on = str(ended).strip() if ended else None
            if started_on and not DATE_RE.fullmatch(started_on):
                raise ValueError('started_on must be YYYY-MM-DD')
            if ended_on and not DATE_RE.fullmatch(ended_on):
                raise ValueError('ended_on must be YYYY-MM-DD')
            if started_on and ended_on and ended_on < started_on:
                raise ValueError('ended_on cannot precede started_on')
            op_id = _edge_id(proposal, source_id, target_id, source_sha)
            if op_id in seen_ids:
                raise ValueError('duplicate deterministic structured memory proposal')
            seen_ids.add(op_id)
            edges.append(EdgeOp(
                id=op_id, source_person_id=source_id, target_person_id=target_id,
                relationship_type=relationship_type, status=status, started_on=started_on,
                ended_on=ended_on, source_kind='user_edited_import', source_system_id='obsidian',
                confidence=confidence, sensitivity_class=sensitivity, source_sha256=source_sha,
            ))
            continue

        raise ValueError(f'unsupported proposal_type: {proposal_type}')

    return dates, edges


def _schema_ready(cur: Any) -> None:
    cur.execute("SELECT to_regclass('llm4life.person_dates') IS NOT NULL, to_regclass('llm4life.person_relationship_edges') IS NOT NULL")
    dates_ok, edges_ok = cur.fetchone()
    if not dates_ok or not edges_ok:
        raise RuntimeError('People memory graph schema is missing; apply migration 006 first')
    cur.execute("SELECT EXISTS (SELECT 1 FROM llm4life.systems WHERE id='obsidian')")
    if not bool(cur.fetchone()[0]):
        raise RuntimeError('obsidian system registry row is missing')


def audit_database(cur: Any, dates: list[DateOp], edges: list[EdgeOp]) -> dict[str, int]:
    person_ids = sorted({str(op.person_id) for op in dates} | {str(op.source_person_id) for op in edges} | {str(op.target_person_id) for op in edges})
    active: set[str] = set()
    if person_ids:
        cur.execute("SELECT id::text FROM llm4life.people WHERE status='active' AND id = ANY(%s::uuid[])", (person_ids,))
        active = {row[0] for row in cur.fetchall()}
    missing_people = len(set(person_ids) - active)

    existing_dates: list[dict[str, Any]] = []
    if person_ids:
        cur.execute("""
            SELECT id::text, person_id::text, date_type, label, year, month, day, recurrence, status
            FROM llm4life.person_dates
            WHERE person_id = ANY(%s::uuid[]) AND status='active'
        """, (person_ids,))
        existing_dates = [
            {'id': r[0], 'person_id': r[1], 'date_type': r[2], 'label': r[3], 'year': r[4], 'month': r[5], 'day': r[6], 'recurrence': r[7], 'status': r[8]}
            for r in cur.fetchall()
        ]

    dates_to_insert = dates_present = date_conflicts = 0
    existing_date_ids = {r['id'] for r in existing_dates}
    for op in dates:
        if str(op.id) in existing_date_ids:
            dates_present += 1
            continue
        same_type = [r for r in existing_dates if r['person_id'] == str(op.person_id) and r['date_type'] == op.date_type]
        exact = [r for r in same_type if r['label'] == op.label and r['year'] == op.year and r['month'] == op.month and r['day'] == op.day and r['recurrence'] == op.recurrence]
        if exact:
            dates_present += 1
        elif op.date_type in SINGLETON_DATE_TYPES and same_type:
            date_conflicts += 1
        else:
            dates_to_insert += 1

    existing_edges: list[dict[str, Any]] = []
    if person_ids:
        cur.execute("""
            SELECT id::text, source_person_id::text, target_person_id::text, relationship_type,
                   status, started_on::text, ended_on::text
            FROM llm4life.person_relationship_edges
            WHERE source_person_id = ANY(%s::uuid[]) OR target_person_id = ANY(%s::uuid[])
        """, (person_ids, person_ids))
        existing_edges = [
            {'id': r[0], 'source': r[1], 'target': r[2], 'type': r[3], 'status': r[4], 'started': r[5], 'ended': r[6]}
            for r in cur.fetchall()
        ]

    edges_to_insert = edges_present = edge_conflicts = 0
    existing_edge_ids = {r['id'] for r in existing_edges}
    for op in edges:
        if str(op.id) in existing_edge_ids:
            edges_present += 1
            continue
        same_slot = [r for r in existing_edges if r['source'] == str(op.source_person_id) and r['target'] == str(op.target_person_id) and r['type'] == op.relationship_type and r['status'] != 'retracted']
        exact = [r for r in same_slot if r['status'] == op.status and r['started'] == op.started_on and r['ended'] == op.ended_on]
        if exact:
            edges_present += 1
        elif same_slot:
            edge_conflicts += 1
        else:
            edges_to_insert += 1

    return {
        'missing_active_people': missing_people,
        'dates_planned': len(dates), 'dates_to_insert': dates_to_insert,
        'dates_already_present': dates_present, 'date_conflicts': date_conflicts,
        'relationship_edges_planned': len(edges), 'relationship_edges_to_insert': edges_to_insert,
        'relationship_edges_already_present': edges_present, 'relationship_edge_conflicts': edge_conflicts,
    }


def apply_operations(cur: Any, dates: list[DateOp], edges: list[EdgeOp]) -> tuple[int, int]:
    dates_inserted = edges_inserted = 0
    for op in dates:
        cur.execute("""
            INSERT INTO llm4life.person_dates (
              id, person_id, date_type, label, year, month, day, recurrence, status,
              source_kind, source_system_id, confidence, sensitivity_class
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'active',%s,%s,%s,%s)
            ON CONFLICT (id) DO NOTHING
        """, (op.id, op.person_id, op.date_type, op.label, op.year, op.month, op.day, op.recurrence,
              op.source_kind, op.source_system_id, op.confidence, op.sensitivity_class))
        dates_inserted += cur.rowcount

    for op in edges:
        cur.execute("""
            INSERT INTO llm4life.person_relationship_edges (
              id, source_person_id, target_person_id, relationship_type, status,
              started_on, ended_on, source_kind, source_system_id, confidence, sensitivity_class
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO NOTHING
        """, (op.id, op.source_person_id, op.target_person_id, op.relationship_type, op.status,
              op.started_on, op.ended_on, op.source_kind, op.source_system_id, op.confidence, op.sensitivity_class))
        edges_inserted += cur.rowcount
    return dates_inserted, edges_inserted


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def main() -> None:
    load_repo_env()
    parser = argparse.ArgumentParser(description='Dry-run or import reviewed People dates and relationship edges into Neon.')
    parser.add_argument('--plan', default=str(DEFAULT_PLAN))
    parser.add_argument('--receipt', default=str(DEFAULT_RECEIPT))
    parser.add_argument('--database-url', default=os.environ.get('DATABASE_URL') or os.environ.get('NEON_DATABASE_URL'))
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--user-authorized', action='store_true')
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit('DATABASE_URL or NEON_DATABASE_URL is required')
    if args.apply and not args.user_authorized:
        raise SystemExit('Refusing --apply without --user-authorized')
    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit('Install requirements-people-phase4.txt first') from exc

    plan_path = Path(args.plan)
    dates, edges = normalize_plan(_load(plan_path))
    with psycopg.connect(args.database_url) as conn:
        with conn.cursor() as cur:
            _schema_ready(cur)
            audit = audit_database(cur, dates, edges)
            blocked = any(audit[key] > 0 for key in ('missing_active_people', 'date_conflicts', 'relationship_edge_conflicts'))
            dates_inserted = edges_inserted = 0
            if args.apply and not blocked:
                dates_inserted, edges_inserted = apply_operations(cur, dates, edges)
                conn.commit()
            else:
                conn.rollback()

    receipt = {
        'schema_version': 1,
        'plan_sha256': hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        'apply_requested': bool(args.apply),
        'user_authorized_flag': bool(args.user_authorized),
        'blocked': blocked,
        **audit,
        'dates_inserted': dates_inserted,
        'relationship_edges_inserted': edges_inserted,
        'privacy': {
            'receipt_contains_names': False,
            'receipt_contains_person_ids': False,
            'receipt_contains_note_paths': False,
            'receipt_contains_raw_evidence': False,
        },
    }
    _write(Path(args.receipt), receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if blocked:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
