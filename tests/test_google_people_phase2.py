from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from google_people_phase2 import CONTACTS_SCOPE, normalize_person  # noqa: E402


class GooglePeoplePhase2Tests(unittest.TestCase):
    def test_normalize_person_preserves_stable_ref_and_minimizes_private_fields(self):
        person = {
            "resourceName": "people/c123",
            "etag": "%etag%",
            "names": [{"displayName": "Alex Example", "familyName": "Example"}],
            "emailAddresses": [{"value": "alex@example.com"}],
            "phoneNumbers": [{"value": "+14165550100"}],
            "addresses": [{"streetAddress": "123 Private St"}],
            "birthdays": [{"date": {"month": 1, "day": 2}}],
            "organizations": [{"name": "Private Org"}],
            "biographies": [{"value": "private note"}],
            "metadata": {"deleted": False},
        }
        result = normalize_person(person, account_scope="google-primary")
        self.assertEqual(result["external_id"], "people/c123")
        self.assertEqual(result["external_id_stability"], "provider_stable")
        self.assertEqual(result["display_name"], "Alex Example")
        self.assertEqual(result["emails"], ["alex@example.com"])
        self.assertEqual(result["phones"], ["+14165550100"])
        self.assertTrue(result["field_presence"]["address"])
        self.assertTrue(result["field_presence"]["birthday"])
        rendered = repr(result)
        self.assertNotIn("123 Private St", rendered)
        self.assertNotIn("Private Org", rendered)
        self.assertNotIn("private note", rendered)

    def test_rejects_non_provider_identifier(self):
        with self.assertRaisesRegex(ValueError, "people/\\.\\.\\."):
            normalize_person({"resourceName": "snapshot-row-1"}, account_scope="google-primary")

    def test_scope_is_write_capable_contacts_scope(self):
        self.assertEqual(CONTACTS_SCOPE, "https://www.googleapis.com/auth/contacts")


if __name__ == "__main__":
    unittest.main()
