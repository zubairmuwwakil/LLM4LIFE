#!/usr/bin/env python3
"""Normalize private Google/Apple contact exports for dry-run People reconciliation.

This tool is read-only with respect to Neon/provider APIs. It writes only local
JSON files. Keep real outputs under .private/people/ or another private path.

Google CSV row IDs are snapshot-only and MUST NOT be persisted as provider refs.
vCard UID values are export identifiers until provider/device semantics are
independently verified.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import quopri
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

EMAIL_HEADER_RE = re.compile(r"^(?:E-?mail|Email)\s+\d+\s+-\s+Value$", re.I)
PHONE_HEADER_RE = re.compile(r"^Phone\s+\d+\s+-\s+Value$", re.I)
VCARD_BLOCK_RE = re.compile(r"BEGIN:VCARD(?P<body>.*?)END:VCARD", re.I | re.S)


@dataclass(frozen=True)
class SnapshotSummary:
    records: int
    with_name: int
    with_email: int
    with_phone: int
    with_address: int
    with_birthday: int
    with_organization: int
    with_notes: int
    stable_export_ids: int
    snapshot_only_ids: int

    def as_dict(self) -> dict[str, int]:
        return {
            "records": self.records,
            "with_name": self.with_name,
            "with_email": self.with_email,
            "with_phone": self.with_phone,
            "with_address": self.with_address,
            "with_birthday": self.with_birthday,
            "with_organization": self.with_organization,
            "with_notes": self.with_notes,
            "stable_export_ids": self.stable_export_ids,
            "snapshot_only_ids": self.snapshot_only_ids,
        }


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _unique_nonempty(values: Iterable[str]) -> list[str]:
    return sorted({_clean(v) for v in values if _clean(v)})


def _snapshot_id(prefix: str, ordinal: int, payload: str) -> str:
    digest = hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()[:20]
    return f"{prefix}:row:{ordinal}:{digest}"


def _google_display_name(row: dict[str, str]) -> str | None:
    for key in ("Name", "Full Name", "File as", "File As"):
        value = _clean(row.get(key))
        if value:
            return value
    parts = [
        _clean(row.get("First Name") or row.get("Given Name")),
        _clean(row.get("Middle Name") or row.get("Additional Name")),
        _clean(row.get("Last Name") or row.get("Family Name") or row.get("Surname")),
    ]
    rendered = " ".join(part for part in parts if part)
    return rendered or None


def parse_google_csv(path: Path, *, account_scope: str) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Google CSV has no header row")
        email_headers = [h for h in reader.fieldnames if h and EMAIL_HEADER_RE.match(h)]
        phone_headers = [h for h in reader.fieldnames if h and PHONE_HEADER_RE.match(h)]
        records: list[dict[str, Any]] = []
        for ordinal, row in enumerate(reader, start=1):
            if not any(_clean(v) for v in row.values() if isinstance(v, str)):
                continue
            canonical_payload = json.dumps(row, ensure_ascii=False, sort_keys=True)
            address_present = any(
                _clean(value)
                for key, value in row.items()
                if key and key.lower().startswith("address ") and isinstance(value, str)
            )
            organization_present = any(
                _clean(value)
                for key, value in row.items()
                if key and "organization" in key.lower() and isinstance(value, str)
            )
            records.append(
                {
                    "source": "google_contacts_export",
                    "account_scope": account_scope,
                    "external_id": _snapshot_id("google-csv", ordinal, canonical_payload),
                    "external_id_stability": "snapshot_only",
                    "display_name": _google_display_name(row),
                    "emails": _unique_nonempty(row.get(h, "") for h in email_headers),
                    "phones": _unique_nonempty(row.get(h, "") for h in phone_headers),
                    "field_presence": {
                        "address": bool(address_present),
                        "birthday": bool(_clean(row.get("Birthday"))),
                        "organization": bool(organization_present),
                        "notes": bool(_clean(row.get("Notes"))),
                    },
                    "archived": False,
                }
            )
    return records


def _unfold_vcard_lines(block: str) -> list[str]:
    raw_lines = block.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    unfolded: list[str] = []
    for line in raw_lines:
        if not line:
            continue
        if line[:1] in {" ", "\t"} and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded


def _decode_vcard_value(raw: str, params: str) -> str:
    value = raw
    if "ENCODING=QUOTED-PRINTABLE" in params.upper():
        try:
            value = quopri.decodestring(value).decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            value = quopri.decodestring(value).decode("latin-1", errors="replace")
    return (
        value.replace(r"\n", "\n")
        .replace(r"\N", "\n")
        .replace(r"\,", ",")
        .replace(r"\;", ";")
        .replace(r"\\", "\\")
        .strip()
    )


def _vcard_property_key(head: str) -> str:
    """Return base property name, handling Apple grouped properties.

    Apple exports commonly use grouped properties such as item1.EMAIL,
    item1.ADR and item1.TEL. The group prefix is metadata; the base property
    after the last dot controls parsing.
    """
    raw_key = head.split(";", 1)[0]
    return raw_key.rsplit(".", 1)[-1].upper()


def _name_from_n(value: str) -> str | None:
    parts = value.split(";")
    family = parts[0] if len(parts) > 0 else ""
    given = parts[1] if len(parts) > 1 else ""
    additional = parts[2] if len(parts) > 2 else ""
    prefix = parts[3] if len(parts) > 3 else ""
    suffix = parts[4] if len(parts) > 4 else ""
    rendered = " ".join(p.strip() for p in (prefix, given, additional, family, suffix) if p.strip())
    return rendered or None


def parse_vcard(path: Path, *, source: str, account_scope: str) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = list(VCARD_BLOCK_RE.finditer(text))
    if not blocks:
        raise ValueError("No BEGIN:VCARD/END:VCARD records found")

    records: list[dict[str, Any]] = []
    for ordinal, match in enumerate(blocks, start=1):
        block_text = match.group(0)
        fn: str | None = None
        n_value: str | None = None
        uid: str | None = None
        emails: list[str] = []
        phones: list[str] = []
        field_presence = {"address": False, "birthday": False, "organization": False, "notes": False}

        for line in _unfold_vcard_lines(match.group("body")):
            if ":" not in line:
                continue
            head, raw_value = line.split(":", 1)
            key = _vcard_property_key(head)
            params = ";".join(head.split(";")[1:])

            if key in {"ADR", "BDAY", "ORG", "NOTE"}:
                presence_key = {
                    "ADR": "address",
                    "BDAY": "birthday",
                    "ORG": "organization",
                    "NOTE": "notes",
                }[key]
                if raw_value.strip():
                    field_presence[presence_key] = True
                continue

            if key not in {"FN", "N", "UID", "EMAIL", "TEL"}:
                continue
            value = _decode_vcard_value(raw_value, params)
            if key == "FN" and value:
                fn = value
            elif key == "N" and value:
                n_value = value
            elif key == "UID" and value:
                uid = value
            elif key == "EMAIL" and value:
                emails.append(value)
            elif key == "TEL" and value:
                phones.append(value)

        if uid:
            external_id = f"vcard-uid:{uid}"
            stability = "export_uid"
        else:
            external_id = _snapshot_id("vcard", ordinal, block_text)
            stability = "snapshot_only"

        records.append(
            {
                "source": source,
                "account_scope": account_scope,
                "external_id": external_id,
                "external_id_stability": stability,
                "display_name": fn or (_name_from_n(n_value) if n_value else None),
                "emails": _unique_nonempty(emails),
                "phones": _unique_nonempty(phones),
                "field_presence": field_presence,
                "archived": False,
            }
        )
    return records


def summarize(records: Iterable[dict[str, Any]]) -> SnapshotSummary:
    rows = list(records)
    stable = sum(1 for r in rows if r.get("external_id_stability") == "export_uid")

    def count_presence(key: str) -> int:
        return sum(bool((r.get("field_presence") or {}).get(key)) for r in rows)

    return SnapshotSummary(
        records=len(rows),
        with_name=sum(bool(r.get("display_name")) for r in rows),
        with_email=sum(bool(r.get("emails")) for r in rows),
        with_phone=sum(bool(r.get("phones")) for r in rows),
        with_address=count_presence("address"),
        with_birthday=count_presence("birthday"),
        with_organization=count_presence("organization"),
        with_notes=count_presence("notes"),
        stable_export_ids=stable,
        snapshot_only_ids=len(rows) - stable,
    )


def write_inventory(records: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def load_normalized(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError(f"{path} must contain a JSON array of objects")
    return payload


def combine(paths: list[Path]) -> list[dict[str, Any]]:
    combined: list[dict[str, Any]] = []
    for path in paths:
        combined.extend(load_normalized(path))
    return combined


def _default_output(name: str) -> Path:
    return Path(".private") / "people" / name


def _print_summary(summary: SnapshotSummary, *, output: Path | None = None) -> None:
    payload: dict[str, Any] = {"summary": summary.as_dict()}
    if output:
        payload["private_output"] = str(output)
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    google = sub.add_parser("google-csv", help="normalize a Google Contacts CSV export")
    google.add_argument("input", type=Path)
    google.add_argument("--account-scope", required=True)
    google.add_argument("--output", type=Path, default=_default_output("google_contacts.json"))

    vcard = sub.add_parser("vcard", help="normalize an Apple/Google vCard export")
    vcard.add_argument("input", type=Path)
    vcard.add_argument("--source", required=True, choices=("apple_contacts", "google_contacts_export"))
    vcard.add_argument("--account-scope", required=True)
    vcard.add_argument("--output", type=Path, default=_default_output("contacts_vcard.json"))

    merged = sub.add_parser("combine", help="combine normalized private inventories")
    merged.add_argument("inputs", nargs="+", type=Path)
    merged.add_argument("--output", type=Path, default=_default_output("combined_contacts.json"))

    summary = sub.add_parser("summarize", help="print aggregate counts only")
    summary.add_argument("input", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "google-csv":
        records = parse_google_csv(args.input, account_scope=args.account_scope)
        write_inventory(records, args.output)
        _print_summary(summarize(records), output=args.output)
    elif args.command == "vcard":
        records = parse_vcard(args.input, source=args.source, account_scope=args.account_scope)
        write_inventory(records, args.output)
        _print_summary(summarize(records), output=args.output)
    elif args.command == "combine":
        records = combine(args.inputs)
        write_inventory(records, args.output)
        _print_summary(summarize(records), output=args.output)
    elif args.command == "summarize":
        _print_summary(summarize(load_normalized(args.input)))


if __name__ == "__main__":
    main()
