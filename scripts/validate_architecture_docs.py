#!/usr/bin/env python3
"""Low-dependency validation for LLM4LIFE public architecture/docs.

This script intentionally validates structure, not private runtime state.
It is safe for the public repository and should remain fast/deterministic so
future agents can run it before declaring documentation/config work complete.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    ROOT / "AGENTS.md",
    ROOT / "README.md",
    ROOT / "system.yaml",
    ROOT / "config" / "domains.yaml",
    ROOT / "config" / "tools.yaml",
    ROOT / "docs" / "STATUS.md",
    ROOT / "docs" / "CURRENT_STATE.md",
    ROOT / "docs" / "ROUTING.md",
    ROOT / "docs" / "TOOL_REGISTRY.md",
    ROOT / "docs" / "PEOPLE.md",
    ROOT / "docs" / "decisions" / "2026-09-03-people-subsystem-architecture.md",
]

YAML_PATHS = [ROOT / "system.yaml", *sorted((ROOT / "config").glob("*.yaml"))]
MARKDOWN_PATHS = [ROOT / "README.md", ROOT / "AGENTS.md", *sorted((ROOT / "docs").rglob("*.md"))]

# Markdown links to web URLs, anchors, mailto, and templated placeholders are not
# local file references and are intentionally ignored.
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def validate_required_files() -> None:
    missing = [path.relative_to(ROOT) for path in REQUIRED_FILES if not path.exists()]
    if missing:
        fail("missing required architecture file(s): " + ", ".join(map(str, missing)))


def validate_yaml() -> None:
    for path in YAML_PATHS:
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
        except Exception as exc:  # pragma: no cover - CI diagnostic path
            fail(f"invalid YAML in {path.relative_to(ROOT)}: {exc}")
        if data is None:
            fail(f"empty YAML document: {path.relative_to(ROOT)}")
        print(f"YAML OK: {path.relative_to(ROOT)}")


def clean_link_target(raw: str) -> str | None:
    target = raw.strip()
    if not target or target.startswith(("#", "http://", "https://", "mailto:", "notion://")):
        return None
    if "{{" in target or "}}" in target:
        return None
    # Optional Markdown title after a path is outside the scope of our simple
    # architecture docs; reject ambiguity instead of trying to guess.
    target = target.split("#", 1)[0]
    return target or None


def validate_markdown_links() -> None:
    errors: list[str] = []
    for path in MARKDOWN_PATHS:
        text = path.read_text(encoding="utf-8")
        for raw in LINK_RE.findall(text):
            target = clean_link_target(raw)
            if target is None:
                continue
            candidate = (path.parent / target).resolve()
            try:
                candidate.relative_to(ROOT.resolve())
            except ValueError:
                # Do not follow links outside the repository.
                continue
            if not candidate.exists():
                errors.append(f"{path.relative_to(ROOT)} -> {target}")
    if errors:
        fail("broken local Markdown link(s):\n  " + "\n  ".join(errors))
    print(f"Markdown links OK: {len(MARKDOWN_PATHS)} files checked")


def validate_people_contract() -> None:
    domains = yaml.safe_load((ROOT / "config" / "domains.yaml").read_text(encoding="utf-8"))
    people_identity = domains.get("domains", {}).get("contact_identity", {})
    relationship_machine = domains.get("domains", {}).get("relationship_machine_state", {})

    if people_identity.get("owner") != "neon":
        fail("config/domains.yaml contact_identity target owner must be neon")
    if relationship_machine.get("owner") != "neon":
        fail("config/domains.yaml relationship_machine_state target owner must be neon")
    if people_identity.get("migration_state") != "phase_0_documented_implementation_not_started":
        fail("People migration state changed; update docs/PEOPLE.md and this validation intentionally")

    print("People Phase 0 contract OK")


def main() -> None:
    validate_required_files()
    validate_yaml()
    validate_markdown_links()
    validate_people_contract()
    print("Architecture documentation validation passed")


if __name__ == "__main__":
    main()
