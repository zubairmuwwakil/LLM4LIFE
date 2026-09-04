#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PERSON_KEY = "llm4life_person_id"
NOTE_KEY = "llm4life_note_id"


def _managed_values(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    lines = text.splitlines()
    values: dict[str, str] = {}
    for idx in range(1, len(lines)):
        if lines[idx] == "---":
            break
        match = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*?)\s*$", lines[idx])
        if not match:
            continue
        key, raw = match.groups()
        if key not in {PERSON_KEY, NOTE_KEY}:
            continue
        raw = raw.strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'\"', "'"}:
            raw = raw[1:-1]
        values[key] = raw
    return values


def _uuid(value: str, field: str) -> str:
    try:
        return str(uuid.UUID(value))
    except ValueError as exc:
        raise ValueError(f"Invalid {field} in managed Obsidian frontmatter") from exc


def discover(vault_root: Path, *, vault_scope: str) -> tuple[dict[str, Any], dict[str, Any]]:
    root = vault_root.resolve()
    if not root.is_dir():
        raise ValueError("vault root does not exist")
    if not vault_scope.strip():
        raise ValueError("vault_scope is required")

    links: list[dict[str, str]] = []
    person_paths: dict[str, str] = {}
    note_owners: dict[str, str] = {}
    markdown_seen = 0

    for path in root.rglob("*.md"):
        relative = path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            continue
        markdown_seen += 1
        managed = _managed_values(path.read_text(encoding="utf-8"))
        raw_person = managed.get(PERSON_KEY)
        if not raw_person:
            continue
        person_id = _uuid(raw_person, PERSON_KEY)
        normalized_path = relative.as_posix()

        prior_path = person_paths.get(person_id)
        if prior_path is not None and prior_path != normalized_path:
            raise ValueError("One People identity is explicitly linked from multiple notes; review manually")
        person_paths[person_id] = normalized_path

        raw_note = managed.get(NOTE_KEY)
        if raw_note:
            note_id = _uuid(raw_note, NOTE_KEY)
            owner = note_owners.get(note_id)
            if owner is not None and owner != person_id:
                raise ValueError("One Obsidian note ID is explicitly linked to multiple People identities")
            note_owners[note_id] = person_id

        links.append({"person_id": person_id, "note_path": normalized_path})

    manifest = {"vault_scope": vault_scope, "links": sorted(links, key=lambda item: item["note_path"])}
    receipt = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "markdown_notes_scanned": markdown_seen,
        "explicit_people_links_found": len(links),
        "name_based_matches_attempted": 0,
        "privacy": {
            "receipt_contains_person_ids": False,
            "receipt_contains_note_ids": False,
            "receipt_contains_note_paths": False,
            "manifest_is_private": True,
        },
    }
    return manifest, receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover only pre-existing explicit LLM4LIFE People links in an Obsidian vault")
    parser.add_argument("--vault-root", default=os.environ.get("OBSIDIAN_VAULT_PATH"))
    parser.add_argument("--vault-scope", default=os.environ.get("OBSIDIAN_VAULT_SCOPE"))
    parser.add_argument("--manifest", default=".private/people/obsidian_mapping_manifest.json")
    parser.add_argument("--receipt", default=".private/people/obsidian_discovery_receipt.json")
    args = parser.parse_args()

    if not args.vault_root or not args.vault_scope:
        raise SystemExit("Set OBSIDIAN_VAULT_PATH and OBSIDIAN_VAULT_SCOPE or pass both flags")
    manifest, receipt = discover(Path(args.vault_root), vault_scope=args.vault_scope)
    manifest_path = Path(args.manifest)
    receipt_path = Path(args.receipt)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print(f"Private explicit-link manifest: {manifest_path}")


if __name__ == "__main__":
    main()
