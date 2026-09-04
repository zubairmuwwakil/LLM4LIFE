import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import apple_google_phase2 as migration


class AppleGooglePhase2Tests(unittest.TestCase):
    def write_vcard(self, text: str) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "contacts.vcf"
        path.write_text(text, encoding="utf-8")
        return path

    def write_google(self, contacts) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "google.json"
        path.write_text(json.dumps({"contacts": contacts}), encoding="utf-8")
        return path

    def test_grouped_vcard_rich_fields_and_yearless_date(self):
        png = base64.b64encode(b"\x89PNG\r\n\x1a\nsynthetic").decode()
        vcard = self.write_vcard(
            "BEGIN:VCARD\nVERSION:3.0\n"
            "N:Doe;Jane;Q;Dr.;Jr.\nFN:Dr. Jane Q Doe Jr.\n"
            "item1.TEL;type=CELL:+14165550123\nitem1.X-ABLabel:_$!<Mobile>!$_\n"
            "item2.EMAIL;type=INTERNET;type=WORK:jane@example.com\n"
            "item3.ADR;type=HOME:;;10 Main St;Toronto;ON;M1M1M1;Canada\n"
            "BDAY;X-APPLE-OMIT-YEAR=1604:1604-05-15\n"
            "ORG:Example Inc;Engineering\nTITLE:Developer\n"
            "item4.X-ABDATE;X-APPLE-OMIT-YEAR=1604:1604-06-13\n"
            "item4.X-ABLabel:_$!<Anniversary>!$_\n"
            "NICKNAME:Jay\nURL:https://example.com/jane\n"
            "X-SOCIALPROFILE;type=WhatsApp;x-userid=14165550123@s.whatsapp.net:x-apple:synthetic\n"
            "NOTE:synthetic private note\n"
            f"PHOTO;ENCODING=b;TYPE=PNG:{png}\nEND:VCARD\n"
        )
        contact = migration.parse_apple_vcard(vcard)[0]
        self.assertEqual(contact.phones[0]["type"], "mobile")
        self.assertEqual(contact.birthday, {"month": 5, "day": 15})
        self.assertEqual(contact.events[0]["type"], "Anniversary")
        self.assertEqual(contact.organizations[0]["title"], "Developer")
        self.assertEqual(contact.social_user_defined[0]["key"], "Social: WhatsApp")
        self.assertTrue(contact.photo_bytes.startswith(b"\x89PNG"))
        self.assertEqual(contact.note, "synthetic private note")

    def test_plan_high_conflict_weak_create_and_empty(self):
        vcard = self.write_vcard(
            "BEGIN:VCARD\nVERSION:3.0\nN:One;Alpha;;;\nFN:Alpha One\n"
            "TEL:+14165550001\nEMAIL:alpha@example.com\nEND:VCARD\n"
            "BEGIN:VCARD\nVERSION:3.0\nN:Two;Bravo;;;\nFN:Bravo Two\n"
            "TEL:+14165550002\nEND:VCARD\n"
            "BEGIN:VCARD\nVERSION:3.0\nN:Three;Charlie;;;\nFN:Charlie Three\nEND:VCARD\n"
            "BEGIN:VCARD\nVERSION:3.0\nN:Four;Delta;;;\nFN:Delta Four\n"
            "TEL:+14165550004\nEND:VCARD\n"
            "BEGIN:VCARD\nVERSION:3.0\nN:;;;;\nEND:VCARD\n"
        )
        google = self.write_google(
            [
                {
                    "external_id": "people/a",
                    "display_name": "Alpha One",
                    "emails": ["alpha@example.com"],
                    "phones": ["+14165550001"],
                    "field_presence": {},
                },
                {
                    "external_id": "people/b",
                    "display_name": "Different Name",
                    "emails": [],
                    "phones": ["+14165550002"],
                    "field_presence": {},
                },
                {
                    "external_id": "people/c",
                    "display_name": "Charlie Three",
                    "emails": [],
                    "phones": [],
                    "field_presence": {},
                },
            ]
        )
        plan = migration.build_plan(vcard, google)
        self.assertEqual(plan["stats"]["updates"], 1)
        self.assertEqual(plan["stats"]["creates"], 1)
        self.assertEqual(plan["stats"]["holds_conflict"], 1)
        self.assertEqual(plan["stats"]["holds_weak"], 1)
        self.assertEqual(plan["stats"]["holds_empty"], 1)
        self.assertFalse(plan["safety"]["provider_deletion_implemented"])

    def test_existing_update_is_additive_and_note_is_held(self):
        apple = migration.AppleContact(
            ordinal=1,
            fingerprint="f",
            emails=[{"value": "new@example.com", "type": "work"}],
            phones=[{"value": "+14165550002", "type": "mobile"}],
            birthday={"month": 5, "day": 15},
            note="do not write me",
        )
        current = {
            "metadata": {"sources": [{"type": "CONTACT", "etag": "etag1"}]},
            "emailAddresses": [
                {
                    "value": "old@example.com",
                    "type": "home",
                    "metadata": {"primary": True},
                }
            ],
            "phoneNumbers": [{"value": "+14165550001", "type": "home"}],
            "birthdays": [{"date": {"month": 6, "day": 1}}],
        }
        body, fields, holds, photo_safe = migration.build_update_payload(current, apple)
        self.assertEqual(
            {item["value"] for item in body["emailAddresses"]},
            {"old@example.com", "new@example.com"},
        )
        self.assertEqual(
            {item["value"] for item in body["phoneNumbers"]},
            {"+14165550001", "+14165550002"},
        )
        self.assertNotIn("birthdays", fields)
        self.assertIn("birthday_conflict", holds)
        self.assertIn("note_requires_classification", holds)
        self.assertNotIn("biographies", body)
        self.assertFalse(photo_safe)

    def test_create_payload_excludes_notes_and_keeps_standard_fields(self):
        apple = migration.AppleContact(
            ordinal=1,
            fingerprint="f",
            display_name="Synthetic Person",
            name={"unstructuredName": "Synthetic Person"},
            emails=[{"value": "s@example.com"}],
            phones=[{"value": "+14165550100"}],
            note="held note",
            social_user_defined=[{"key": "Social: example", "value": "id123"}],
        )
        body, holds = migration.build_create_payload(apple)
        self.assertEqual(body["names"][0]["unstructuredName"], "Synthetic Person")
        self.assertIn("userDefined", body)
        self.assertNotIn("biographies", body)
        self.assertEqual(holds, ["note_requires_classification"])

    def test_photo_only_overwrites_absent_or_default_contact_photo(self):
        apple = migration.AppleContact(
            ordinal=1,
            fingerprint="f",
            photo_bytes=b"\x89PNG\r\n\x1a\nfoo",
        )
        base = {"metadata": {"sources": [{"type": "CONTACT", "etag": "e"}]}}
        self.assertTrue(migration.build_update_payload(base, apple)[3])
        with_default = {
            **base,
            "photos": [
                {
                    "default": True,
                    "metadata": {"source": {"type": "CONTACT"}},
                }
            ],
        }
        self.assertTrue(migration.build_update_payload(with_default, apple)[3])
        with_real = {
            **base,
            "photos": [
                {
                    "default": False,
                    "metadata": {"source": {"type": "CONTACT"}},
                }
            ],
        }
        self.assertFalse(migration.build_update_payload(with_real, apple)[3])


if __name__ == "__main__":
    unittest.main()
