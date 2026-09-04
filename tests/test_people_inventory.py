from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from people_inventory import (  # noqa: E402
    combine,
    parse_google_csv,
    parse_vcard,
    summarize,
    write_inventory,
)


class PeopleInventoryTests(unittest.TestCase):
    def test_google_csv_preserves_match_fields_but_not_private_field_values(self):
        headers = [
            "First Name", "Middle Name", "Last Name",
            "Email 1 - Value", "Phone 1 - Value",
            "Address 1 - Street", "Birthday", "Organization Name", "Notes",
        ]
        row = {
            "First Name": "Alex",
            "Middle Name": "Q",
            "Last Name": "Example",
            "Email 1 - Value": "alex@example.com",
            "Phone 1 - Value": "416-555-0100",
            "Address 1 - Street": "123 Private St",
            "Birthday": "2000-01-02",
            "Organization Name": "Private Org",
            "Notes": "private note body",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "google.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=headers)
                writer.writeheader()
                writer.writerow(row)
            records = parse_google_csv(path, account_scope="google-primary")

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["source"], "google_contacts_export")
        self.assertEqual(record["display_name"], "Alex Q Example")
        self.assertEqual(record["emails"], ["alex@example.com"])
        self.assertEqual(record["phones"], ["416-555-0100"])
        self.assertEqual(record["external_id_stability"], "snapshot_only")
        self.assertTrue(record["field_presence"]["address"])
        self.assertTrue(record["field_presence"]["birthday"])
        self.assertTrue(record["field_presence"]["organization"])
        self.assertTrue(record["field_presence"]["notes"])

        rendered = json.dumps(record)
        self.assertNotIn("123 Private St", rendered)
        self.assertNotIn("2000-01-02", rendered)
        self.assertNotIn("Private Org", rendered)
        self.assertNotIn("private note body", rendered)

    def test_google_snapshot_id_is_deterministic_for_same_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "google.csv"
            path.write_text("Name,Email 1 - Value\nAlex Example,alex@example.com\n", encoding="utf-8")
            first = parse_google_csv(path, account_scope="google-primary")
            second = parse_google_csv(path, account_scope="google-primary")
        self.assertEqual(first, second)
        self.assertTrue(first[0]["external_id"].startswith("google-csv:row:1:"))

    def test_vcard_uid_is_preserved_and_sensitive_nonmatching_values_are_not_retained(self):
        payload = """BEGIN:VCARD
VERSION:3.0
UID:apple-export-123
FN:Alex Example
EMAIL;TYPE=HOME:alex@example.com
TEL;TYPE=CELL:+1 416 555 0100
ADR;TYPE=HOME:;;123 Private St;Whitby;ON;L1A1A1;Canada
BDAY:2000-01-02
ORG:Private Org
NOTE:private narrative
PHOTO;ENCODING=b;TYPE=JPEG:ABCDEFG
END:VCARD
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contacts.vcf"
            path.write_text(payload, encoding="utf-8")
            records = parse_vcard(path, source="apple_contacts", account_scope="icloud-primary")

        record = records[0]
        self.assertEqual(record["external_id"], "vcard-uid:apple-export-123")
        self.assertEqual(record["external_id_stability"], "export_uid")
        self.assertEqual(record["emails"], ["alex@example.com"])
        self.assertEqual(record["phones"], ["+1 416 555 0100"])
        self.assertEqual(record["display_name"], "Alex Example")
        self.assertEqual(record["field_presence"], {
            "address": True,
            "birthday": True,
            "organization": True,
            "notes": True,
        })
        rendered = json.dumps(record)
        for secret in ("123 Private St", "2000-01-02", "Private Org", "private narrative", "ABCDEFG"):
            self.assertNotIn(secret, rendered)

    def test_vcard_without_uid_gets_snapshot_only_id_and_n_fallback(self):
        payload = """BEGIN:VCARD
VERSION:3.0
N:Example;Alex;Q;;Jr.
EMAIL:alex@example.com
END:VCARD
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contacts.vcf"
            path.write_text(payload, encoding="utf-8")
            records = parse_vcard(path, source="apple_contacts", account_scope="icloud-primary")

        self.assertEqual(records[0]["display_name"], "Alex Q Example Jr.")
        self.assertEqual(records[0]["external_id_stability"], "snapshot_only")
        self.assertTrue(records[0]["external_id"].startswith("vcard:row:1:"))

    def test_summary_reports_only_aggregate_presence_counts(self):
        records = [
            {
                "display_name": "Alex", "emails": ["a@example.com"], "phones": [],
                "field_presence": {"address": True, "birthday": False, "organization": False, "notes": False},
                "external_id_stability": "export_uid",
            },
            {
                "display_name": None, "emails": [], "phones": ["4165550100"],
                "field_presence": {"address": False, "birthday": True, "organization": True, "notes": True},
                "external_id_stability": "snapshot_only",
            },
        ]
        result = summarize(records).as_dict()
        self.assertEqual(result, {
            "records": 2,
            "with_name": 1,
            "with_email": 1,
            "with_phone": 1,
            "with_address": 1,
            "with_birthday": 1,
            "with_organization": 1,
            "with_notes": 1,
            "stable_export_ids": 1,
            "snapshot_only_ids": 1,
        })

    def test_combine_round_trip_is_deterministic(self):
        first = [{
            "source": "google_contacts_export", "account_scope": "g", "external_id": "google-csv:row:1:a",
            "external_id_stability": "snapshot_only", "display_name": "Alex", "emails": [], "phones": [],
            "field_presence": {}, "archived": False,
        }]
        second = [{
            "source": "apple_contacts", "account_scope": "a", "external_id": "vcard-uid:1",
            "external_id_stability": "export_uid", "display_name": "Jordan", "emails": [], "phones": [],
            "field_presence": {}, "archived": False,
        }]
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.json"
            b = Path(tmp) / "b.json"
            write_inventory(first, a)
            write_inventory(second, b)
            self.assertEqual(combine([a, b]), first + second)


if __name__ == "__main__":
    unittest.main()
