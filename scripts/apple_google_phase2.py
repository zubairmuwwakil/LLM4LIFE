#!/usr/bin/env python3
"""Plan and apply the Apple -> Google Contacts Phase 2 migration.

Privacy model:
- Real vCards, Google snapshots, plans, OAuth tokens and receipts stay under .private/.
- This script may be committed publicly; tests must use synthetic contacts only.

Safety model:
- Dry-run planning is the default workflow.
- Existing Google contacts are enriched additively after a fresh GET.
- Existing Google names are never overwritten.
- Conflicting/weak identity matches are held for review.
- Notes are preserved in the private plan/receipt as a count only and are not
  written automatically because narrative-vs-contact-note classification is pending.
- No contact delete API is implemented anywhere in this module.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import quopri
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

GOOGLE_BASE = "https://people.googleapis.com/v1"
GET_FIELDS = ",".join(
    [
        "addresses",
        "birthdays",
        "emailAddresses",
        "events",
        "metadata",
        "names",
        "nicknames",
        "organizations",
        "phoneNumbers",
        "photos",
        "urls",
        "userDefined",
    ]
)
POST_MUTATE_FIELDS = GET_FIELDS
VCARD_RE = re.compile(r"BEGIN:VCARD\r?\n(?P<body>.*?)\r?\nEND:VCARD", re.I | re.S)
SPACE_RE = re.compile(r"\s+")
NON_PHONE_RE = re.compile(r"[^0-9+]")
APPLE_LABEL_RE = re.compile(r"^_\$!<(?P<label>.+)>!\$_$")


@dataclass
class AppleContact:
    ordinal: int
    fingerprint: str
    display_name: str | None = None
    name: dict[str, str] | None = None
    emails: list[dict[str, str]] = field(default_factory=list)
    phones: list[dict[str, str]] = field(default_factory=list)
    addresses: list[dict[str, str]] = field(default_factory=list)
    birthday: dict[str, int] | None = None
    organizations: list[dict[str, Any]] = field(default_factory=list)
    urls: list[dict[str, str]] = field(default_factory=list)
    social_user_defined: list[dict[str, str]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    nicknames: list[dict[str, str]] = field(default_factory=list)
    note: str | None = None
    photo_bytes: bytes | None = None

    def has_meaningful_contact_data(self) -> bool:
        return bool(
            self.display_name
            or self.emails
            or self.phones
            or self.addresses
            or self.birthday
            or self.organizations
            or self.urls
            or self.social_user_defined
            or self.events
            or self.nicknames
            or self.note
            or self.photo_bytes
        )


def _nfkc(value: str) -> str:
    return unicodedata.normalize("NFKC", value)


def normalize_name(value: str | None) -> str | None:
    if not value:
        return None
    value = SPACE_RE.sub(" ", _nfkc(value).casefold().strip())
    return value or None


def normalize_email(value: str) -> str | None:
    value = _nfkc(value).strip().casefold()
    if not value or "@" not in value:
        return None
    local, domain = value.rsplit("@", 1)
    if not local or not domain:
        return None
    try:
        domain = domain.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    return f"{local}@{domain}"


def normalize_phone(value: str, default_region: str = "CA") -> tuple[str | None, bool]:
    raw = _nfkc(value).strip()
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
        return cleaned, 8 <= len(digits) <= 15
    if default_region.upper() in {"CA", "US"}:
        if len(digits) == 10:
            return "+1" + digits, True
        if len(digits) == 11 and digits.startswith("1"):
            return "+" + digits, True
    return digits, False


def _unfold_lines(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        if line.startswith((" ", "\t")) and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def _decode_text(raw: str, params_text: str = "") -> str:
    value = raw
    if "ENCODING=QUOTED-PRINTABLE" in params_text.upper():
        decoded = quopri.decodestring(value)
        try:
            value = decoded.decode("utf-8")
        except UnicodeDecodeError:
            value = decoded.decode("latin-1", errors="replace")
    return (
        value.replace(r"\n", "\n")
        .replace(r"\N", "\n")
        .replace(r"\,", ",")
        .replace(r"\;", ";")
        .replace(r"\\", "\\")
        .strip()
    )


def _split_escaped(raw: str, sep: str = ";") -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    escaped = False
    for ch in raw:
        if escaped:
            buf.extend(["\\", ch])
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == sep:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if escaped:
        buf.append("\\")
    parts.append("".join(buf))
    return parts


def _head_parts(head: str) -> tuple[str | None, str, dict[str, list[str]]]:
    first, *rest = head.split(";")
    if "." in first:
        group, key = first.rsplit(".", 1)
    else:
        group, key = None, first
    params: dict[str, list[str]] = {}
    for item in rest:
        if not item:
            continue
        if "=" in item:
            key_name, value = item.split("=", 1)
            vals = [piece.strip('"') for piece in value.split(",") if piece]
            params.setdefault(key_name.upper(), []).extend(vals)
        else:
            params.setdefault("TYPE", []).append(item)
    return group, key.upper(), params


def _clean_label(value: str | None) -> str | None:
    if not value:
        return None
    value = _decode_text(value)
    match = APPLE_LABEL_RE.match(value)
    if match:
        value = match.group("label")
    return value.strip() or None


def _field_type(params: dict[str, list[str]], group_label: str | None) -> str | None:
    label = _clean_label(group_label)
    if label:
        lowered = label.casefold()
        common = {
            "home": "home",
            "work": "work",
            "mobile": "mobile",
            "iphone": "mobile",
            "main": "main",
            "other": "other",
        }
        return common.get(lowered, label)
    ignored = {"internet", "voice", "pref"}
    for raw in params.get("TYPE", []):
        low = raw.casefold()
        if low in ignored:
            continue
        if low in {"cell", "iphone"}:
            return "mobile"
        if low in {"home", "work", "main", "other"}:
            return low
        return raw
    return None


def _date_value(raw: str, params: dict[str, list[str]]) -> dict[str, int] | None:
    value = raw.strip().replace("--", "").replace("-", "")
    if not value.isdigit():
        return None
    year: int | None = None
    if len(value) == 8:
        year = int(value[:4])
        month = int(value[4:6])
        day = int(value[6:8])
    elif len(value) == 4:
        month = int(value[:2])
        day = int(value[2:])
    else:
        return None
    omit_year = any(v == "1604" for v in params.get("X-APPLE-OMIT-YEAR", []))
    if year == 1604 and omit_year:
        year = None
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    result = {"month": month, "day": day}
    if year is not None:
        result["year"] = year
    return result


def _name_from_n(raw: str) -> tuple[dict[str, str] | None, str | None]:
    parts = [_decode_text(v) for v in _split_escaped(raw)]
    parts += [""] * (5 - len(parts))
    family, given, middle, prefix, suffix = parts[:5]
    writable = {
        k: v
        for k, v in {
            "familyName": family,
            "givenName": given,
            "middleName": middle,
            "honorificPrefix": prefix,
            "honorificSuffix": suffix,
        }.items()
        if v
    }
    rendered = " ".join(v for v in (prefix, given, middle, family, suffix) if v) or None
    return (writable or None), rendered


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _dedupe_items(items: Iterable[dict[str, Any]], key) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        marker = str(key(item))
        if not marker or marker in seen:
            continue
        seen.add(marker)
        out.append(item)
    return out


def parse_apple_vcard(path: Path) -> list[AppleContact]:
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = list(VCARD_RE.finditer(text))
    if not matches:
        raise ValueError("No BEGIN:VCARD/END:VCARD records found")
    contacts: list[AppleContact] = []
    for ordinal, match in enumerate(matches, 1):
        block = match.group(0)
        lines = _unfold_lines(match.group("body"))
        group_labels: dict[str, str] = {}
        for line in lines:
            if ":" not in line:
                continue
            head, raw = line.split(":", 1)
            group, key, _ = _head_parts(head)
            if group and key == "X-ABLABEL":
                group_labels[group] = _decode_text(raw, ";".join(head.split(";")[1:]))

        contact = AppleContact(
            ordinal=ordinal,
            fingerprint=hashlib.sha256(block.encode("utf-8", errors="replace")).hexdigest(),
        )
        fn: str | None = None
        n_rendered: str | None = None
        pending_org_title: str | None = None

        for line in lines:
            if ":" not in line:
                continue
            head, raw = line.split(":", 1)
            group, key, params = _head_parts(head)
            params_text = ";".join(head.split(";")[1:])
            label = group_labels.get(group or "")

            if key == "FN":
                fn = _decode_text(raw, params_text) or None
            elif key == "N":
                contact.name, n_rendered = _name_from_n(raw)
            elif key == "EMAIL":
                value = _decode_text(raw, params_text)
                if value:
                    item = {"value": value}
                    typ = _field_type(params, label)
                    if typ:
                        item["type"] = typ
                    contact.emails.append(item)
            elif key == "TEL":
                value = _decode_text(raw, params_text)
                if value:
                    item = {"value": value}
                    typ = _field_type(params, label)
                    if typ:
                        item["type"] = typ
                    contact.phones.append(item)
            elif key == "ADR":
                parts = [_decode_text(v) for v in _split_escaped(raw)]
                parts += [""] * (7 - len(parts))
                po, extended, street, city, region, postal, country = parts[:7]
                item = {
                    k: v
                    for k, v in {
                        "poBox": po,
                        "extendedAddress": extended,
                        "streetAddress": street,
                        "city": city,
                        "region": region,
                        "postalCode": postal,
                        "country": country,
                    }.items()
                    if v
                }
                typ = _field_type(params, label)
                if typ:
                    item["type"] = typ
                if item:
                    contact.addresses.append(item)
            elif key == "BDAY" and contact.birthday is None:
                contact.birthday = _date_value(raw, params)
            elif key == "ORG":
                parts = [_decode_text(v) for v in _split_escaped(raw)]
                org: dict[str, Any] = {}
                if parts and parts[0]:
                    org["name"] = parts[0]
                if len(parts) > 1 and parts[1]:
                    org["department"] = parts[1]
                if pending_org_title:
                    org["title"] = pending_org_title
                    pending_org_title = None
                if org:
                    contact.organizations.append(org)
            elif key == "TITLE":
                title = _decode_text(raw, params_text)
                if contact.organizations:
                    contact.organizations[-1].setdefault("title", title)
                elif title:
                    pending_org_title = title
            elif key == "URL":
                value = _decode_text(raw, params_text)
                if value:
                    item = {"value": value}
                    typ = _field_type(params, label)
                    if typ:
                        item["type"] = typ
                    contact.urls.append(item)
            elif key == "X-SOCIALPROFILE":
                value = _decode_text(raw, params_text)
                if not value:
                    continue
                if value.lower().startswith(("http://", "https://")):
                    contact.urls.append({"value": value, "type": "social"})
                else:
                    service = next(iter(params.get("TYPE", [])), None) or "Apple social profile"
                    userid = next(iter(params.get("X-USERID", [])), None)
                    contact.social_user_defined.append(
                        {"key": f"Social: {service}", "value": userid or value}
                    )
            elif key == "X-ABDATE":
                date = _date_value(raw, params)
                if date:
                    contact.events.append({"date": date, "type": _clean_label(label) or "other"})
            elif key == "NICKNAME":
                value = _decode_text(raw, params_text)
                if value:
                    contact.nicknames.append({"value": value, "type": "DEFAULT"})
            elif key == "NOTE":
                value = _decode_text(raw, params_text)
                if value:
                    contact.note = value
            elif key == "PHOTO":
                encoding = {v.casefold() for v in params.get("ENCODING", [])}
                if "b" in encoding or "base64" in encoding:
                    try:
                        photo = base64.b64decode(raw, validate=False)
                    except Exception:
                        photo = b""
                    if photo.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")):
                        contact.photo_bytes = photo

        if pending_org_title:
            contact.organizations.append({"title": pending_org_title})
        contact.display_name = fn or n_rendered
        if contact.name is None and contact.display_name:
            contact.name = {"unstructuredName": contact.display_name}
        contact.emails = _dedupe_items(
            contact.emails,
            lambda x: normalize_email(x.get("value", "")) or x.get("value", ""),
        )
        contact.phones = _dedupe_items(
            contact.phones,
            lambda x: normalize_phone(x.get("value", ""))[0] or x.get("value", ""),
        )
        contact.addresses = _dedupe_items(contact.addresses, _canonical_json)
        contact.urls = _dedupe_items(
            contact.urls, lambda x: x.get("value", "").strip().casefold()
        )
        contact.events = _dedupe_items(contact.events, _canonical_json)
        contact.nicknames = _dedupe_items(
            contact.nicknames, lambda x: x.get("value", "").casefold()
        )
        contact.social_user_defined = _dedupe_items(
            contact.social_user_defined, _canonical_json
        )
        contacts.append(contact)
    return contacts


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _google_signals(item: dict[str, Any]) -> tuple[set[str], set[str], str | None]:
    emails = {v for raw in item.get("emails") or [] if (v := normalize_email(raw))}
    phones: set[str] = set()
    for raw in item.get("phones") or []:
        normalized, strong = normalize_phone(raw)
        if normalized and strong:
            phones.add(normalized)
    return emails, phones, normalize_name(item.get("display_name"))


def _apple_signals(item: AppleContact) -> tuple[set[str], set[str], str | None]:
    emails = {
        v
        for raw in item.emails
        if (v := normalize_email(raw.get("value", "")))
    }
    phones: set[str] = set()
    for raw in item.phones:
        normalized, strong = normalize_phone(raw.get("value", ""))
        if normalized and strong:
            phones.add(normalized)
    return emails, phones, normalize_name(item.display_name)


def _pair_band(apple: AppleContact, google: dict[str, Any]) -> str | None:
    apple_emails, apple_phones, apple_name = _apple_signals(apple)
    google_emails, google_phones, google_name = _google_signals(google)
    shared_email = bool(apple_emails & google_emails)
    shared_phone = bool(apple_phones & google_phones)
    same_name = bool(apple_name and google_name and apple_name == google_name)
    conflicting_names = bool(apple_name and google_name and apple_name != google_name)
    strong_count = int(shared_email) + int(shared_phone)
    if strong_count and conflicting_names:
        return "conflict"
    if strong_count >= 2:
        return "high"
    if strong_count and same_name:
        return "high"
    if strong_count:
        return "conflict"
    if same_name:
        return "weak"
    return None


def build_plan(vcard_path: Path, google_snapshot_path: Path) -> dict[str, Any]:
    apple = parse_apple_vcard(vcard_path)
    payload = json.loads(google_snapshot_path.read_text(encoding="utf-8"))
    google = payload.get("contacts") if isinstance(payload, dict) else payload
    if not isinstance(google, list):
        raise ValueError("Google snapshot must contain a contacts array")
    for item in google:
        resource_name = item.get("external_id") if isinstance(item, dict) else None
        if not isinstance(resource_name, str) or not resource_name.startswith("people/"):
            raise ValueError("Google snapshot contains a non-stable provider ID")

    high_by_apple: dict[int, list[str]] = {}
    high_by_google: dict[str, list[int]] = {}
    conflict_by_apple: dict[int, list[str]] = {}
    weak_by_apple: dict[int, list[str]] = {}
    google_by_id = {item["external_id"]: item for item in google}

    for apple_contact in apple:
        for google_contact in google:
            band = _pair_band(apple_contact, google_contact)
            if band == "high":
                high_by_apple.setdefault(apple_contact.ordinal, []).append(
                    google_contact["external_id"]
                )
                high_by_google.setdefault(google_contact["external_id"], []).append(
                    apple_contact.ordinal
                )
            elif band == "conflict":
                conflict_by_apple.setdefault(apple_contact.ordinal, []).append(
                    google_contact["external_id"]
                )
            elif band == "weak":
                weak_by_apple.setdefault(apple_contact.ordinal, []).append(
                    google_contact["external_id"]
                )

    if any(len(values) != 1 for values in high_by_apple.values()) or any(
        len(values) != 1 for values in high_by_google.values()
    ):
        raise ValueError(
            "High-confidence match graph is not one-to-one; refusing to plan writes"
        )

    operations: list[dict[str, Any]] = []
    potential_fields: dict[str, int] = {}
    for apple_contact in apple:
        base = {
            "apple_ordinal": apple_contact.ordinal,
            "apple_fingerprint": apple_contact.fingerprint,
        }
        if apple_contact.ordinal in high_by_apple:
            resource_name = high_by_apple[apple_contact.ordinal][0]
            google_contact = google_by_id[resource_name]
            operation = {
                **base,
                "action": "update",
                "google_external_id": resource_name,
            }
            potentials: list[str] = []
            apple_emails, apple_phones, _ = _apple_signals(apple_contact)
            google_emails, google_phones, _ = _google_signals(google_contact)
            if apple_emails - google_emails:
                potentials.append("emailAddresses")
            if apple_phones - google_phones:
                potentials.append("phoneNumbers")
            presence = google_contact.get("field_presence") or {}
            checks = [
                (apple_contact.addresses, "address", "addresses"),
                (apple_contact.birthday, "birthday", "birthdays"),
                (apple_contact.organizations, "organization", "organizations"),
                (
                    apple_contact.urls or apple_contact.social_user_defined,
                    "urls",
                    "urls",
                ),
                (apple_contact.events, "events", "events"),
            ]
            for apple_value, presence_key, google_field in checks:
                if apple_value and not bool(presence.get(presence_key)):
                    potentials.append(google_field)
            if apple_contact.nicknames:
                potentials.append("nicknames")
            if apple_contact.photo_bytes:
                potentials.append("photo")
            if apple_contact.note:
                potentials.append("note_held")
            operation["potential_fields"] = sorted(set(potentials))
            for field_name in operation["potential_fields"]:
                potential_fields[field_name] = potential_fields.get(field_name, 0) + 1
            operations.append(operation)
        elif apple_contact.ordinal in conflict_by_apple:
            operations.append(
                {**base, "action": "hold", "reason": "identity_conflict"}
            )
        elif apple_contact.ordinal in weak_by_apple:
            operations.append(
                {**base, "action": "hold", "reason": "name_only_weak_match"}
            )
        elif apple_contact.has_meaningful_contact_data():
            operations.append({**base, "action": "create"})
        else:
            operations.append({**base, "action": "hold", "reason": "empty_contact"})

    stats: dict[str, Any] = {
        "apple_contacts": len(apple),
        "google_contacts": len(google),
        "updates": sum(op["action"] == "update" for op in operations),
        "creates": sum(op["action"] == "create" for op in operations),
        "holds_conflict": sum(
            op.get("reason") == "identity_conflict" for op in operations
        ),
        "holds_weak": sum(
            op.get("reason") == "name_only_weak_match" for op in operations
        ),
        "holds_empty": sum(op.get("reason") == "empty_contact" for op in operations),
        "potential_fields": dict(sorted(potential_fields.items())),
        "apple_notes_held": sum(bool(item.note) for item in apple),
        "apple_photos": sum(bool(item.photo_bytes) for item in apple),
    }
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "safety": {
            "provider_deletion_implemented": False,
            "existing_names_overwritten": False,
            "notes_auto_written": False,
            "conflict_or_weak_matches_written": False,
            "updates_are_additive_after_fresh_get": True,
        },
        "sources": {
            "apple_vcard_sha256": _file_sha256(vcard_path),
            "google_snapshot_sha256": _file_sha256(google_snapshot_path),
        },
        "stats": stats,
        "operations": operations,
    }


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def _clean_existing(field_name: str, item: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "emailAddresses": {"value", "type"},
        "phoneNumbers": {"value", "type"},
        "addresses": {
            "formattedValue",
            "type",
            "poBox",
            "streetAddress",
            "extendedAddress",
            "city",
            "region",
            "postalCode",
            "country",
            "countryCode",
        },
        "birthdays": {"date", "text"},
        "events": {"date", "type"},
        "nicknames": {"value", "type"},
        "organizations": {
            "type",
            "startDate",
            "endDate",
            "current",
            "name",
            "phoneticName",
            "department",
            "title",
            "jobDescription",
            "symbol",
            "domain",
            "location",
            "costCenter",
            "fullTimeEquivalentMillipercent",
        },
        "urls": {"value", "type"},
        "userDefined": {"key", "value"},
    }[field_name]
    return {
        key: value
        for key, value in item.items()
        if key in allowed and value not in (None, "", [], {})
    }


def _sig(field_name: str, item: dict[str, Any]) -> str:
    if field_name == "emailAddresses":
        return normalize_email(item.get("value", "")) or item.get("value", "").casefold()
    if field_name == "phoneNumbers":
        return normalize_phone(item.get("value", ""))[0] or item.get("value", "")
    if field_name in {"urls", "nicknames"}:
        return str(item.get("value", "")).strip().casefold()
    return _canonical_json(_clean_existing(field_name, item))


def _union_field(
    field_name: str,
    existing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    output = [_clean_existing(field_name, item) for item in existing]
    seen = {_sig(field_name, item) for item in output}
    changed = False
    for raw in incoming:
        item = _clean_existing(field_name, raw)
        marker = _sig(field_name, item)
        if marker and marker not in seen:
            seen.add(marker)
            output.append(item)
            changed = True
    return output, changed


def _same_date(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return {
        key: a.get(key)
        for key in ("year", "month", "day")
        if a.get(key) is not None
    } == {
        key: b.get(key)
        for key in ("year", "month", "day")
        if b.get(key) is not None
    }


def build_update_payload(
    current: dict[str, Any], apple: AppleContact
) -> tuple[dict[str, Any], list[str], list[str], bool]:
    body: dict[str, Any] = {
        "metadata": {
            "sources": [
                source
                for source in (current.get("metadata") or {}).get("sources", [])
                if source.get("type") == "CONTACT"
            ]
        }
    }
    changed_fields: list[str] = []
    holds: list[str] = []

    incoming = {
        "emailAddresses": apple.emails,
        "phoneNumbers": apple.phones,
        "addresses": apple.addresses,
        "organizations": apple.organizations,
        "urls": apple.urls,
        "events": apple.events,
        "nicknames": apple.nicknames,
        "userDefined": apple.social_user_defined,
    }
    for field_name, values in incoming.items():
        if not values:
            continue
        merged, changed = _union_field(
            field_name, current.get(field_name) or [], values
        )
        if changed:
            body[field_name] = merged
            changed_fields.append(field_name)

    if apple.birthday:
        existing_birthdays = current.get("birthdays") or []
        if not existing_birthdays:
            body["birthdays"] = [{"date": apple.birthday}]
            changed_fields.append("birthdays")
        elif not any(
            _same_date((birthday.get("date") or {}), apple.birthday)
            for birthday in existing_birthdays
        ):
            holds.append("birthday_conflict")

    if apple.note:
        holds.append("note_requires_classification")

    photos = current.get("photos") or []
    contact_photos = [
        photo
        for photo in photos
        if ((photo.get("metadata") or {}).get("source") or {}).get("type")
        == "CONTACT"
    ]
    photo_safe = bool(apple.photo_bytes) and (
        not contact_photos or all(bool(photo.get("default")) for photo in contact_photos)
    )
    return body, sorted(set(changed_fields)), sorted(set(holds)), photo_safe


def build_create_payload(apple: AppleContact) -> tuple[dict[str, Any], list[str]]:
    body: dict[str, Any] = {}
    if apple.name:
        body["names"] = [apple.name]
    mapping = {
        "emailAddresses": apple.emails,
        "phoneNumbers": apple.phones,
        "addresses": apple.addresses,
        "organizations": apple.organizations,
        "urls": apple.urls,
        "events": apple.events,
        "nicknames": apple.nicknames,
        "userDefined": apple.social_user_defined,
    }
    for key, values in mapping.items():
        if values:
            body[key] = values
    if apple.birthday:
        body["birthdays"] = [{"date": apple.birthday}]
    holds = ["note_requires_classification"] if apple.note else []
    return body, holds


def _get_person(session, resource_name: str) -> dict[str, Any]:
    response = session.get(
        f"{GOOGLE_BASE}/{resource_name}",
        params={
            "personFields": GET_FIELDS,
            "sources": "READ_SOURCE_TYPE_CONTACT",
        },
        timeout=60,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"People GET failed ({response.status_code}): {response.text[:500]}"
        )
    return response.json()


def _patch_person(
    session, resource_name: str, body: dict[str, Any], fields: list[str]
) -> dict[str, Any]:
    response = session.patch(
        f"{GOOGLE_BASE}/{resource_name}:updateContact",
        params={
            "updatePersonFields": ",".join(fields),
            "personFields": POST_MUTATE_FIELDS,
        },
        json=body,
        timeout=60,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"People update failed ({response.status_code}): {response.text[:500]}"
        )
    return response.json()


def _create_person(session, body: dict[str, Any]) -> dict[str, Any]:
    response = session.post(
        f"{GOOGLE_BASE}/people:createContact",
        params={"personFields": POST_MUTATE_FIELDS},
        json=body,
        timeout=60,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"People create failed ({response.status_code}): {response.text[:500]}"
        )
    return response.json()


def _update_photo(session, resource_name: str, photo_bytes: bytes) -> None:
    response = session.patch(
        f"{GOOGLE_BASE}/{resource_name}:updateContactPhoto",
        json={"photoBytes": base64.b64encode(photo_bytes).decode("ascii")},
        timeout=60,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"People photo update failed ({response.status_code}): {response.text[:500]}"
        )


def _load_google_session(client_secret: Path, token_path: Path):
    try:
        from google.auth.transport.requests import AuthorizedSession
    except ImportError as exc:
        raise SystemExit(
            "Missing Google OAuth dependencies; install requirements-people-phase2.txt"
        ) from exc
    try:
        from google_people_phase2 import _load_credentials
    except ImportError as exc:
        raise SystemExit(
            "Run this script from the repository so scripts/google_people_phase2.py is importable"
        ) from exc
    return AuthorizedSession(_load_credentials(client_secret, token_path))


def _validate_plan_sources(
    plan: dict[str, Any], vcard: Path, snapshot: Path
) -> None:
    expected = plan.get("sources") or {}
    if expected.get("apple_vcard_sha256") != _file_sha256(vcard):
        raise ValueError("Apple vCard digest changed after planning; regenerate plan")
    if expected.get("google_snapshot_sha256") != _file_sha256(snapshot):
        raise ValueError("Google snapshot digest changed after planning; regenerate plan")


def apply_plan(
    plan_path: Path,
    vcard_path: Path,
    google_snapshot_path: Path,
    receipt_path: Path,
    *,
    client_secret: Path,
    token_path: Path,
    refreshed_snapshot_path: Path,
    apply: bool,
) -> dict[str, Any]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    _validate_plan_sources(plan, vcard_path, google_snapshot_path)
    apple = {item.ordinal: item for item in parse_apple_vcard(vcard_path)}
    for operation in plan.get("operations") or []:
        apple_contact = apple.get(operation.get("apple_ordinal"))
        if (
            not apple_contact
            or apple_contact.fingerprint != operation.get("apple_fingerprint")
        ):
            raise ValueError(
                "Plan no longer maps exactly to Apple vCard; regenerate plan"
            )

    if not apply:
        return {"dry_run": True, **(plan.get("stats") or {})}

    session = _load_google_session(client_secret, token_path)
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    else:
        receipt = {
            "schema_version": 1,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "results": {},
        }
    results: dict[str, Any] = receipt.setdefault("results", {})

    counts = {
        "updated": 0,
        "created": 0,
        "skipped_receipt": 0,
        "held": 0,
        "field_holds": 0,
        "photos_written": 0,
    }
    for operation in plan.get("operations") or []:
        fingerprint = operation["apple_fingerprint"]
        existing_result = results.get(fingerprint)
        if existing_result and existing_result.get("status") == "success":
            counts["skipped_receipt"] += 1
            continue
        action = operation["action"]
        apple_contact = apple[operation["apple_ordinal"]]
        if action == "hold":
            counts["held"] += 1
            results[fingerprint] = {
                "status": "held",
                "reason": operation.get("reason"),
            }
            write_json_atomic(receipt_path, receipt)
            continue
        try:
            if action == "update":
                resource_name = operation["google_external_id"]
                current = _get_person(session, resource_name)
                body, fields, holds, photo_safe = build_update_payload(
                    current, apple_contact
                )
                if fields:
                    updated = _patch_person(session, resource_name, body, fields)
                    resource_name = updated.get("resourceName") or resource_name
                    counts["updated"] += 1
                if photo_safe and apple_contact.photo_bytes:
                    _update_photo(session, resource_name, apple_contact.photo_bytes)
                    counts["photos_written"] += 1
                counts["field_holds"] += len(holds)
                results[fingerprint] = {
                    "status": "success",
                    "action": "update",
                    "google_external_id": resource_name,
                    "updated_fields": fields,
                    "field_holds": holds,
                    "photo_written": bool(photo_safe and apple_contact.photo_bytes),
                }
            elif action == "create":
                body, holds = build_create_payload(apple_contact)
                if not body:
                    results[fingerprint] = {
                        "status": "held",
                        "reason": "no_writable_fields",
                    }
                    counts["held"] += 1
                else:
                    created = _create_person(session, body)
                    resource_name = created.get("resourceName")
                    if not isinstance(resource_name, str) or not resource_name.startswith(
                        "people/"
                    ):
                        raise RuntimeError(
                            "Create succeeded without stable people/... resourceName"
                        )
                    if apple_contact.photo_bytes:
                        _update_photo(
                            session, resource_name, apple_contact.photo_bytes
                        )
                        counts["photos_written"] += 1
                    counts["created"] += 1
                    counts["field_holds"] += len(holds)
                    results[fingerprint] = {
                        "status": "success",
                        "action": "create",
                        "google_external_id": resource_name,
                        "field_holds": holds,
                        "photo_written": bool(apple_contact.photo_bytes),
                    }
            else:
                raise ValueError(f"Unknown action: {action}")
        except Exception as exc:
            results[fingerprint] = {
                "status": "error",
                "action": action,
                "error": str(exc)[:1000],
            }
            receipt["last_error_at"] = datetime.now(timezone.utc).isoformat()
            write_json_atomic(receipt_path, receipt)
            raise
        receipt["updated_at"] = datetime.now(timezone.utc).isoformat()
        write_json_atomic(receipt_path, receipt)

    try:
        from google_people_phase2 import enumerate_saved_contacts, write_snapshot
    except ImportError as exc:
        raise SystemExit("scripts/google_people_phase2.py must be importable") from exc
    contacts, sync_token = enumerate_saved_contacts(
        client_secret=client_secret,
        token_path=token_path,
        account_scope="google-primary",
    )
    write_snapshot(
        contacts,
        output=refreshed_snapshot_path,
        account_scope="google-primary",
        next_sync_token=sync_token,
    )
    receipt["completed_at"] = datetime.now(timezone.utc).isoformat()
    receipt["aggregate"] = counts
    receipt["refreshed_google_contacts"] = len(contacts)
    write_json_atomic(receipt_path, receipt)
    return {
        **counts,
        "refreshed_google_contacts": len(contacts),
        "private_receipt": str(receipt_path),
        "refreshed_snapshot": str(refreshed_snapshot_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser(
        "plan", help="build a private deterministic Apple -> Google migration plan"
    )
    plan.add_argument(
        "--apple-vcard",
        type=Path,
        default=Path(".private/people/apple_contacts.vcf"),
    )
    plan.add_argument(
        "--google-snapshot",
        type=Path,
        default=Path(".private/people/google_people_live.json"),
    )
    plan.add_argument(
        "--output",
        type=Path,
        default=Path(".private/people/apple_google_plan.json"),
    )

    apply_parser = sub.add_parser(
        "apply", help="validate or explicitly apply a private migration plan"
    )
    apply_parser.add_argument(
        "--plan",
        type=Path,
        default=Path(".private/people/apple_google_plan.json"),
    )
    apply_parser.add_argument(
        "--apple-vcard",
        type=Path,
        default=Path(".private/people/apple_contacts.vcf"),
    )
    apply_parser.add_argument(
        "--google-snapshot",
        type=Path,
        default=Path(".private/people/google_people_live.json"),
    )
    apply_parser.add_argument(
        "--receipt",
        type=Path,
        default=Path(".private/people/apple_google_apply_receipt.json"),
    )
    apply_parser.add_argument(
        "--client-secret",
        type=Path,
        default=Path(".private/people/google-oauth-client.json"),
    )
    apply_parser.add_argument(
        "--token",
        type=Path,
        default=Path(".private/people/google-people-token.json"),
    )
    apply_parser.add_argument(
        "--refreshed-snapshot",
        type=Path,
        default=Path(".private/people/google_people_live_after_apple.json"),
    )
    apply_parser.add_argument(
        "--apply", action="store_true", help="required to perform provider writes"
    )

    args = parser.parse_args()
    if args.command == "plan":
        value = build_plan(args.apple_vcard, args.google_snapshot)
        write_json_atomic(args.output, value)
        print(
            json.dumps(
                {"private_plan": str(args.output), **value["stats"]},
                indent=2,
                sort_keys=True,
            )
        )
    elif args.command == "apply":
        result = apply_plan(
            args.plan,
            args.apple_vcard,
            args.google_snapshot,
            args.receipt,
            client_secret=args.client_secret,
            token_path=args.token,
            refreshed_snapshot_path=args.refreshed_snapshot,
            apply=args.apply,
        )
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
