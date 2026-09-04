#!/usr/bin/env python3
"""Deterministic, read-only duplicate-candidate generation for People imports.

This tool never mutates provider data or Neon. It consumes a private inventory
file locally and emits candidate pairs. Real contact payloads must never be
committed to the public repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

SPACE_RE = re.compile(r"\s+")
NON_PHONE_RE = re.compile(r"[^0-9+]")


@dataclass(frozen=True)
class ContactRecord:
    source: str
    account_scope: str
    external_id: str
    display_name: str | None
    emails: tuple[str, ...]
    phones: tuple[str, ...]
    archived: bool = False

    @property
    def source_key(self) -> str:
        return f"{self.source}|{self.account_scope}|{self.external_id}"


def normalize_name(value: str | None) -> str | None:
    if not value:
        return None
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    normalized = SPACE_RE.sub(" ", normalized)
    return normalized or None


def normalize_email(value: str) -> str | None:
    value = unicodedata.normalize("NFKC", value).strip().casefold()
    if not value or "@" not in value:
        return None
    local, domain = value.rsplit("@", 1)
    if not local or not domain:
        return None
    try:
        domain = domain.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    # Intentionally do not strip dots or plus tags. Provider-specific alias
    # normalization can collapse distinct addresses and is unsafe for identity.
    return f"{local}@{domain}"


def normalize_phone(value: str, default_region: str = "CA") -> tuple[str | None, bool]:
    raw = unicodedata.normalize("NFKC", value).strip()
    if not raw:
        return None, False
    if raw.startswith("00"):
        raw = "+" + raw[2:]
    cleaned = NON_PHONE_RE.sub("", raw)
    if cleaned.count("+") > 1 or ("+" in cleaned and not cleaned.startswith("+")):
        return None, False
    digits = cleaned[1:] if cleaned.startswith("+") else cleaned
    if not digits.isdigit():
        return None, False

    if cleaned.startswith("+"):
        # E.164 max is 15 digits; require a plausible minimum before treating
        # the value as a strong identity signal.
        return (cleaned, 8 <= len(digits) <= 15)

    if default_region.upper() in {"CA", "US"}:
        if len(digits) == 10:
            return "+1" + digits, True
        if len(digits) == 11 and digits.startswith("1"):
            return "+" + digits, True

    # Preserve a weak normalized value for reporting, but never use it alone as
    # a strong merge signal.
    return digits, False


def _tuple_strings(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
        raise ValueError("emails and phones must be arrays of strings")
    return tuple(values)


def parse_record(raw: dict[str, Any]) -> ContactRecord:
    required = ("source", "account_scope", "external_id")
    missing = [key for key in required if not isinstance(raw.get(key), str) or not raw[key].strip()]
    if missing:
        raise ValueError(f"missing/non-string required field(s): {', '.join(missing)}")
    name = raw.get("display_name")
    if name is not None and not isinstance(name, str):
        raise ValueError("display_name must be a string or null")
    archived = raw.get("archived", False)
    if not isinstance(archived, bool):
        raise ValueError("archived must be boolean")
    return ContactRecord(
        source=raw["source"].strip(),
        account_scope=raw["account_scope"].strip(),
        external_id=raw["external_id"].strip(),
        display_name=name.strip() if isinstance(name, str) and name.strip() else None,
        emails=_tuple_strings(raw.get("emails")),
        phones=_tuple_strings(raw.get("phones")),
        archived=archived,
    )


def load_inventory(path: Path) -> list[ContactRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("inventory must be a JSON array")

    by_key: dict[str, ContactRecord] = {}
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("every inventory item must be an object")
        record = parse_record(item)
        existing = by_key.get(record.source_key)
        if existing is None:
            by_key[record.source_key] = record
        elif existing != record:
            raise ValueError(f"conflicting rerun rows for provider ref {record.source_key}")
        # Exact provider-ref reruns with identical content are intentionally
        # collapsed here; they are not duplicate-person candidates.
    return [by_key[key] for key in sorted(by_key)]


def resolve_exact_provider_ref(
    record: ContactRecord, provider_ref_to_person_id: Mapping[str, str]
) -> str | None:
    """Resolve the strongest identity signal before any candidate matching.

    Provider field edits (including renames) do not affect this lookup because
    the source/account/external ID tuple is the identity boundary.
    """
    return provider_ref_to_person_id.get(record.source_key)


def _signals(record: ContactRecord, default_region: str) -> tuple[set[str], set[str], str | None]:
    emails = {v for raw in record.emails if (v := normalize_email(raw))}
    strong_phones: set[str] = set()
    for raw in record.phones:
        normalized, strong = normalize_phone(raw, default_region=default_region)
        if normalized and strong:
            strong_phones.add(normalized)
    return emails, strong_phones, normalize_name(record.display_name)


def _candidate_id(a: str, b: str) -> str:
    left, right = sorted((a, b))
    digest = hashlib.sha256(f"{left}\n{right}".encode("utf-8")).hexdigest()
    return f"pcand_{digest[:20]}"


def generate_candidates(
    records: Iterable[ContactRecord],
    *,
    default_region: str = "CA",
    include_name_only: bool = False,
) -> list[dict[str, Any]]:
    records = list(records)
    signal_map = {r.source_key: _signals(r, default_region) for r in records}
    output: list[dict[str, Any]] = []

    for i, left in enumerate(records):
        left_emails, left_phones, left_name = signal_map[left.source_key]
        for right in records[i + 1 :]:
            right_emails, right_phones, right_name = signal_map[right.source_key]
            shared_emails = sorted(left_emails & right_emails)
            shared_phones = sorted(left_phones & right_phones)
            same_name = bool(left_name and right_name and left_name == right_name)
            conflicting_names = bool(left_name and right_name and left_name != right_name)

            reasons: list[str] = []
            if shared_emails:
                reasons.append("shared_normalized_email")
            if shared_phones:
                reasons.append("shared_strong_phone")
            if same_name:
                reasons.append("same_normalized_name")
            if left.archived or right.archived:
                reasons.append("archived_source_record")

            has_strong = bool(shared_emails or shared_phones)
            independent_strong_count = int(bool(shared_emails)) + int(bool(shared_phones))

            if has_strong and conflicting_names:
                band = "conflict"
                reasons.append("strong_contact_point_with_conflicting_name")
            elif independent_strong_count >= 2:
                band = "high"
            elif has_strong and same_name:
                band = "high"
            elif has_strong:
                # A single shared address/phone without supporting evidence is
                # reviewable but not auto-mergeable (shared inboxes/numbers exist).
                band = "conflict"
                reasons.append("single_strong_signal_without_support")
            elif same_name and include_name_only:
                band = "weak"
                reasons.append("name_only_never_auto_merge")
            else:
                continue

            ordered_refs = sorted((left.source_key, right.source_key))
            output.append(
                {
                    "candidate_id": _candidate_id(left.source_key, right.source_key),
                    "left_ref": ordered_refs[0],
                    "right_ref": ordered_refs[1],
                    "confidence_band": band,
                    "reasons": sorted(set(reasons)),
                    "automatic_merge": False,
                }
            )

    return sorted(output, key=lambda item: item["candidate_id"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path, help="private local JSON inventory")
    parser.add_argument("--output", type=Path, help="write candidate JSON here; stdout if omitted")
    parser.add_argument("--default-region", default="CA")
    parser.add_argument("--include-name-only", action="store_true")
    args = parser.parse_args()

    candidates = generate_candidates(
        load_inventory(args.inventory),
        default_region=args.default_region,
        include_name_only=args.include_name_only,
    )
    rendered = json.dumps(candidates, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
