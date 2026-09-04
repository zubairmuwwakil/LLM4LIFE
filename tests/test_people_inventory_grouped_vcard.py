from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from people_inventory import parse_vcard  # noqa: E402


class GroupedAppleVCardTests(unittest.TestCase):
    def test_grouped_email_phone_and_address_are_parsed(self):
        payload = """BEGIN:VCARD
VERSION:3.0
FN:Alex Example
N:Example;Alex;;;
item1.EMAIL;TYPE=HOME:alex@example.com
item1.X-ABLabel:Home
item2.TEL;TYPE=CELL:+1 416 555 0100
item2.X-ABLabel:Mobile
item3.ADR;TYPE=HOME:;;123 Private St;Whitby;ON;L1A1A1;Canada
item3.X-ABLabel:Home
END:VCARD
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contacts.vcf"
            path.write_text(payload, encoding="utf-8")
            records = parse_vcard(path, source="apple_contacts", account_scope="icloud-primary")

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["emails"], ["alex@example.com"])
        self.assertEqual(record["phones"], ["+1 416 555 0100"])
        self.assertTrue(record["field_presence"]["address"])
        rendered = json.dumps(record)
        self.assertNotIn("123 Private St", rendered)


if __name__ == "__main__":
    unittest.main()
