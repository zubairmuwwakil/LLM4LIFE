#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CORE_FIELDS = ("address", "birthday", "organization", "urls")
ADVISORY_FIELDS = ("photos",)


def _norm_email(value: str) -> str:
    return value.strip().lower()


def _norm_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", value or "")
    if len(digits) < 7:
        return ""
    if len(digits) == 11 and digits.startswith("1"):
        return digits[-10:]
    if len(digits) > 10:
        return digits[-10:]
    return digits


def _norm_name(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _values(contact: dict[str, Any], key: str, normalizer) -> set[str]:
    out: set[str] = set()
    for value in contact.get(key) or []:
        normalized = normalizer(str(value))
        if normalized:
            out.add(normalized)
    return out


def _presence(contact: dict[str, Any]) -> dict[str, bool]:
    raw = contact.get("field_presence") or {}
    return {str(k): bool(v) for k, v in raw.items()}


def _build_index(contacts: list[dict[str, Any]]) -> dict[str, Any]:
    emails: dict[str, set[int]] = defaultdict(set)
    phones: dict[str, set[int]] = defaultdict(set)
    names: dict[str, set[int]] = defaultdict(set)
    per_contact: list[dict[str, Any]] = []
    for idx, contact in enumerate(contacts):
        c_emails = _values(contact, "emails", _norm_email)
        c_phones = _values(contact, "phones", _norm_phone)
        c_name = _norm_name(contact.get("display_name"))
        per_contact.append(
            {
                "emails": c_emails,
                "phones": c_phones,
                "name": c_name,
                "presence": _presence(contact),
            }
        )
        for value in c_emails:
            emails[value].add(idx)
        for value in c_phones:
            phones[value].add(idx)
        if c_name:
            names[c_name].add(idx)
    return {"emails": emails, "phones": phones, "names": names, "contacts": per_contact}


def _candidate_ids(g: dict[str, Any], idx: dict[str, Any]) -> tuple[set[int], str]:
    strong: set[int] = set()
    for email in g["emails"]:
        strong.update(idx["emails"].get(email, ()))
    for phone in g["phones"]:
        strong.update(idx["phones"].get(phone, ()))
    if strong:
        return strong, "strong"

    name = g["name"]
    if name and len(idx["names"].get(name, ())) == 1:
        return set(idx["names"][name]), "unique_name"
    return set(), "none"


def _choose_candidate(g: dict[str, Any], candidates: set[int], idx: dict[str, Any]) -> int | None:
    if not candidates:
        return None
    if len(candidates) == 1:
        return next(iter(candidates))

    def score(candidate_idx: int) -> tuple[int, int, int]:
        a = idx["contacts"][candidate_idx]
        email_overlap = len(g["emails"] & a["emails"])
        phone_overlap = len(g["phones"] & a["phones"])
        name_match = int(bool(g["name"]) and g["name"] == a["name"])
        return (email_overlap + phone_overlap, name_match, -candidate_idx)

    return max(candidates, key=score)


def _evaluate_container(
    google_contacts: list[dict[str, Any]],
    apple_contacts: list[dict[str, Any]],
) -> dict[str, Any]:
    g_idx = _build_index(google_contacts)
    a_idx = _build_index(apple_contacts)

    google_name_counts = {name: len(ids) for name, ids in g_idx["names"].items()}

    matched = 0
    strong = 0
    unique_name = 0
    missing_core = defaultdict(int)
    expected_core = defaultdict(int)
    missing_advisory = defaultdict(int)
    expected_advisory = defaultdict(int)

    for g in g_idx["contacts"]:
        candidates, mode = _candidate_ids(g, a_idx)
        if mode == "unique_name" and google_name_counts.get(g["name"], 0) != 1:
            candidates = set()
            mode = "none"
        chosen = _choose_candidate(g, candidates, a_idx)
        if chosen is None:
            continue
        matched += 1
        if mode == "strong":
            strong += 1
        elif mode == "unique_name":
            unique_name += 1

        a = a_idx["contacts"][chosen]
        g_presence = g["presence"]
        a_presence = a["presence"]

        if g["emails"]:
            expected_core["emailAddresses"] += 1
            if not (g["emails"] & a["emails"]):
                missing_core["emailAddresses"] += 1
        if g["phones"]:
            expected_core["phoneNumbers"] += 1
            if not (g["phones"] & a["phones"]):
                missing_core["phoneNumbers"] += 1

        for field in CORE_FIELDS:
            if g_presence.get(field, False):
                expected_core[field] += 1
                if not a_presence.get(field, False):
                    missing_core[field] += 1

        for field in ADVISORY_FIELDS:
            if g_presence.get(field, False):
                expected_advisory[field] += 1
                if not a_presence.get(field, False):
                    missing_advisory[field] += 1

    total = len(google_contacts)
    expected_core_total = sum(expected_core.values())
    missing_core_total = sum(missing_core.values())

    return {
        "apple_contacts": len(apple_contacts),
        "google_contacts": total,
        "matched_google_contacts": matched,
        "strong_matches": strong,
        "unique_name_matches": unique_name,
        "coverage": (matched / total) if total else 0.0,
        "expected_core_field_instances": expected_core_total,
        "missing_core_field_instances": missing_core_total,
        "core_field_loss_rate": (
            missing_core_total / expected_core_total if expected_core_total else 0.0
        ),
        "missing_core_by_field": dict(sorted(missing_core.items())),
        "expected_core_by_field": dict(sorted(expected_core.items())),
        "missing_advisory_by_field": dict(sorted(missing_advisory.items())),
        "expected_advisory_by_field": dict(sorted(expected_advisory.items())),
    }


def verify(
    google_snapshot: dict[str, Any],
    apple_snapshot: dict[str, Any],
    *,
    min_coverage: float,
    max_core_field_loss_rate: float,
) -> dict[str, Any]:
    google_contacts = google_snapshot.get("contacts") or []
    if not google_contacts:
        raise ValueError("Google snapshot has no contacts")

    containers = apple_snapshot.get("containers") or []
    if not containers:
        raise ValueError("Apple snapshot has no containers")

    evaluations: list[dict[str, Any]] = []
    for container in containers:
        result = _evaluate_container(google_contacts, container.get("contacts") or [])
        result["container_type"] = container.get("type") or "unknown"
        evaluations.append(result)

    best_idx = max(
        range(len(evaluations)),
        key=lambda i: (
            evaluations[i]["coverage"],
            -evaluations[i]["core_field_loss_rate"],
            evaluations[i]["strong_matches"],
            evaluations[i]["apple_contacts"],
        ),
    )
    best = evaluations[best_idx]

    verified = (
        best["coverage"] >= min_coverage
        and best["core_field_loss_rate"] <= max_core_field_loss_rate
    )

    public_candidates = [
        {
            "container_type": item["container_type"],
            "apple_contacts": item["apple_contacts"],
            "coverage": round(item["coverage"], 6),
            "strong_matches": item["strong_matches"],
            "unique_name_matches": item["unique_name_matches"],
            "core_field_loss_rate": round(item["core_field_loss_rate"], 6),
        }
        for item in evaluations
    ]

    return {
        "schema_version": 1,
        "verified": verified,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "google_contacts": len(google_contacts),
        "apple_containers_seen": len(containers),
        "selected_container_index": best_idx,
        "selected_container_type": best["container_type"],
        "selected_container_contacts": best["apple_contacts"],
        "matched_google_contacts": best["matched_google_contacts"],
        "strong_matches": best["strong_matches"],
        "unique_name_matches": best["unique_name_matches"],
        "coverage": round(best["coverage"], 6),
        "expected_core_field_instances": best["expected_core_field_instances"],
        "missing_core_field_instances": best["missing_core_field_instances"],
        "core_field_loss_rate": round(best["core_field_loss_rate"], 6),
        "missing_core_by_field": best["missing_core_by_field"],
        "expected_core_by_field": best["expected_core_by_field"],
        "missing_advisory_by_field": best["missing_advisory_by_field"],
        "expected_advisory_by_field": best["expected_advisory_by_field"],
        "thresholds": {
            "min_coverage": min_coverage,
            "max_core_field_loss_rate": max_core_field_loss_rate,
        },
        "container_candidates": public_candidates,
        "privacy": {
            "receipt_contains_names": False,
            "receipt_contains_emails": False,
            "receipt_contains_phones": False,
            "receipt_contains_addresses": False,
            "receipt_contains_provider_contact_ids": False,
            "raw_apple_snapshot_is_private": True,
            "raw_google_snapshot_is_private": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify that a macOS Contacts container has synchronized the post-cutover Google Contacts state."
    )
    parser.add_argument("--google-snapshot", required=True)
    parser.add_argument("--apple-snapshot", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--min-coverage", type=float, default=0.98)
    parser.add_argument("--max-core-field-loss-rate", type=float, default=0.01)
    args = parser.parse_args()

    google_snapshot = json.loads(Path(args.google_snapshot).read_text())
    apple_snapshot = json.loads(Path(args.apple_snapshot).read_text())
    receipt = verify(
        google_snapshot,
        apple_snapshot,
        min_coverage=args.min_coverage,
        max_core_field_loss_rate=args.max_core_field_loss_rate,
    )

    receipt_path = Path(args.receipt)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    print(json.dumps(receipt, indent=2, sort_keys=True))
    if not receipt["verified"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
