#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PERSON_KEY = "llm4life_person_id"
NOTE_KEY = "llm4life_note_id"
LINK_CONTRACT = "obsidian_frontmatter_v1"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _uuid(value: str, *, field: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"Invalid UUID for {field}") from exc


def _safe_note_path(vault_root: Path, note_path: str) -> tuple[Path, str]:
    relative = Path(note_path)
    if relative.is_absolute() or relative.suffix.lower() != ".md":
        raise ValueError("Obsidian note_path must be a relative .md path")
    root = vault_root.resolve()
    resolved = (root / relative).resolve()
    try:
        normalized = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("Obsidian note_path escapes the configured vault") from exc
    if not resolved.is_file():
        raise ValueError("Mapped Obsidian note does not exist")
    return resolved, normalized


def _parse_frontmatter(text: str) -> tuple[list[str], str, bool]:
    if not text.startswith("---\n"):
        return [], text, False
    lines = text.splitlines(keepends=True)
    for idx in range(1, len(lines)):
        if lines[idx].rstrip("\r\n") == "---":
            frontmatter = [line.rstrip("\r\n") for line in lines[1:idx]]
            body = "".join(lines[idx + 1 :])
            return frontmatter, body, True
    raise ValueError("Malformed YAML frontmatter: opening delimiter has no closing delimiter")


def _managed_values(frontmatter: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    pattern = re.compile(r"^([A-Za-z0-9_-]+)\s*:\s*(.*?)\s*$")
    for line in frontmatter:
        match = pattern.match(line)
        if not match:
            continue
        key, raw = match.groups()
        if key not in {PERSON_KEY, NOTE_KEY}:
            continue
        if key in values:
            raise ValueError(f"Duplicate managed frontmatter key: {key}")
        raw = raw.strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'\"', "'"}:
            raw = raw[1:-1]
        values[key] = raw
    return values


def _render_frontmatter(
    original: list[str], *, person_id: str, note_id: str, had_frontmatter: bool, body: str
) -> str:
    replacement = {
        PERSON_KEY: f'{PERSON_KEY}: "{person_id}"',
        NOTE_KEY: f'{NOTE_KEY}: "{note_id}"',
    }
    seen: set[str] = set()
    out: list[str] = []
    key_pattern = re.compile(r"^([A-Za-z0-9_-]+)\s*:")
    for line in original:
        match = key_pattern.match(line)
        key = match.group(1) if match else None
        if key in replacement:
            out.append(replacement[key])
            seen.add(key)
        else:
            out.append(line)
    for key in (PERSON_KEY, NOTE_KEY):
        if key not in seen:
            out.append(replacement[key])

    prefix = "---\n" + "\n".join(out) + "\n---\n"
    if not had_frontmatter and body and not body.startswith("\n"):
        prefix += "\n"
    return prefix + body


def _atomic_write(path: Path, content: str) -> None:
    stat = path.stat()
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    os.chmod(temp_path, stat.st_mode)
    os.replace(temp_path, path)


def build_link_plan(
    *,
    vault_root: Path,
    manifest: dict[str, Any],
    apply_frontmatter: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    vault_scope = str(manifest.get("vault_scope") or "").strip()
    if not vault_scope:
        raise ValueError("manifest.vault_scope is required")
    links = manifest.get("links")
    if not isinstance(links, list):
        raise ValueError("manifest.links must be a list")

    plan_entries: list[dict[str, Any]] = []
    note_ids: set[str] = set()
    normalized_paths: dict[str, str] = {}
    changed = 0
    already_linked = 0

    for raw in links:
        if not isinstance(raw, dict):
            raise ValueError("Each manifest link must be an object")
        person_id = _uuid(raw.get("person_id"), field="person_id")
        note_file, normalized_path = _safe_note_path(vault_root, str(raw.get("note_path") or ""))

        prior_person = normalized_paths.get(normalized_path)
        if prior_person is not None and prior_person != person_id:
            raise ValueError("One Obsidian note cannot map to two People identities")
        normalized_paths[normalized_path] = person_id

        text = note_file.read_text(encoding="utf-8")
        frontmatter, body, had_frontmatter = _parse_frontmatter(text)
        managed = _managed_values(frontmatter)

        existing_person = managed.get(PERSON_KEY)
        if existing_person:
            existing_person = _uuid(existing_person, field=PERSON_KEY)
            if existing_person != person_id:
                raise ValueError("Existing Obsidian person link conflicts with manifest")

        existing_note_id = managed.get(NOTE_KEY)
        if existing_note_id:
            note_id = _uuid(existing_note_id, field=NOTE_KEY)
        else:
            note_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"https://llm4life.local/obsidian/{vault_scope}/{normalized_path}",
                )
            )

        if note_id in note_ids:
            raise ValueError("Duplicate Obsidian note ID detected in mapping manifest")
        note_ids.add(note_id)

        rendered = _render_frontmatter(
            frontmatter,
            person_id=person_id,
            note_id=note_id,
            had_frontmatter=had_frontmatter,
            body=body,
        )
        if rendered != text:
            if apply_frontmatter:
                _atomic_write(note_file, rendered)
            changed += 1
        else:
            already_linked += 1

        plan_entries.append(
            {
                "internal_type": "person",
                "internal_id": person_id,
                "system_id": "obsidian",
                "account_scope": vault_scope,
                "external_id": f"note:{note_id}",
                "ref_kind": "narrative",
                "metadata": {"link_contract": LINK_CONTRACT},
            }
        )

    plan = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system_id": "obsidian",
        "account_scope": vault_scope,
        "link_contract": LINK_CONTRACT,
        "refs": plan_entries,
    }
    receipt = {
        "schema_version": 1,
        "generated_at": plan["generated_at"],
        "links_requested": len(links),
        "refs_planned": len(plan_entries),
        "frontmatter_apply_requested": apply_frontmatter,
        "notes_changed_or_would_change": changed,
        "notes_already_linked": already_linked,
        "conflicts": 0,
        "privacy": {
            "receipt_contains_person_ids": False,
            "receipt_contains_note_ids": False,
            "receipt_contains_note_paths": False,
            "receipt_contains_narrative": False,
            "private_plan_contains_link_ids": True,
            "narrative_copied_to_neon": False,
        },
    }
    return plan, receipt


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create explicit People↔Obsidian linkage metadata without name-based matching "
            "or copying narrative text into Neon."
        )
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--vault-root", default=os.environ.get("OBSIDIAN_VAULT_PATH"))
    parser.add_argument(
        "--plan", default=".private/people/obsidian_external_refs_plan.json"
    )
    parser.add_argument(
        "--receipt", default=".private/people/obsidian_link_receipt.json"
    )
    parser.add_argument("--apply-frontmatter", action="store_true")
    args = parser.parse_args()

    if not args.vault_root:
        raise SystemExit("Set OBSIDIAN_VAULT_PATH or pass --vault-root")

    plan, receipt = build_link_plan(
        vault_root=Path(args.vault_root),
        manifest=_load_json(Path(args.manifest)),
        apply_frontmatter=args.apply_frontmatter,
    )

    plan_path = Path(args.plan)
    receipt_path = Path(args.receipt)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    print(json.dumps(receipt, indent=2, sort_keys=True))
    print(f"Private linkage plan: {plan_path}")
    print(f"Private aggregate receipt: {receipt_path}")


if __name__ == "__main__":
    main()
