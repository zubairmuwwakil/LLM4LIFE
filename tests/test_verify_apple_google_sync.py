import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_apple_google_sync.py"
SPEC = importlib.util.spec_from_file_location("verify_apple_google_sync", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MOD)


def g(name, email=None, phone=None, **presence):
    return {
        "display_name": name,
        "emails": [email] if email else [],
        "phones": [phone] if phone else [],
        "field_presence": {
            "address": bool(presence.get("address")),
            "birthday": bool(presence.get("birthday")),
            "organization": bool(presence.get("organization")),
            "urls": bool(presence.get("urls")),
            "photos": bool(presence.get("photos")),
        },
    }


def a(name, email=None, phone=None, **presence):
    return g(name, email, phone, **presence)


class AppleGoogleSyncVerifierTests(unittest.TestCase):
    def test_selects_full_sync_container_and_verifies(self):
        google = {
            "contacts": [
                g("Alice Example", "alice@example.com", "+1 416 555 0101", birthday=True),
                g("Bob Example", phone="416-555-0102", organization=True),
                g("Cara Example", "cara@example.com", address=True, urls=True),
            ]
        }
        apple = {
            "containers": [
                {"type": "carddav", "contacts": [a("Alice Example", "alice@example.com", "+14165550101", birthday=True)]},
                {
                    "type": "carddav",
                    "contacts": [
                        a("Alice Example", "alice@example.com", "+14165550101", birthday=True),
                        a("Bob Example", phone="(416) 555-0102", organization=True),
                        a("Cara Example", "CARA@example.com", address=True, urls=True),
                    ],
                },
            ]
        }
        receipt = MOD.verify(
            google, apple, min_coverage=1.0, max_core_field_loss_rate=0.0
        )
        self.assertTrue(receipt["verified"])
        self.assertEqual(receipt["selected_container_index"], 1)
        self.assertEqual(receipt["matched_google_contacts"], 3)
        self.assertEqual(receipt["coverage"], 1.0)
        self.assertEqual(receipt["core_field_loss_rate"], 0.0)

    def test_fails_when_contact_sync_coverage_is_low(self):
        google = {
            "contacts": [
                g("Alice Example", "alice@example.com"),
                g("Bob Example", phone="4165550102"),
                g("Cara Example", "cara@example.com"),
            ]
        }
        apple = {
            "containers": [
                {"type": "carddav", "contacts": [a("Alice Example", "alice@example.com")]}
            ]
        }
        receipt = MOD.verify(
            google, apple, min_coverage=0.98, max_core_field_loss_rate=0.01
        )
        self.assertFalse(receipt["verified"])
        self.assertLess(receipt["coverage"], 0.98)

    def test_detects_material_field_loss(self):
        google = {
            "contacts": [
                g("Alice Example", "alice@example.com", birthday=True, address=True),
            ]
        }
        apple = {
            "containers": [
                {
                    "type": "carddav",
                    "contacts": [a("Alice Example", "alice@example.com")],
                }
            ]
        }
        receipt = MOD.verify(
            google, apple, min_coverage=1.0, max_core_field_loss_rate=0.0
        )
        self.assertFalse(receipt["verified"])
        self.assertGreater(receipt["core_field_loss_rate"], 0.0)
        self.assertEqual(receipt["missing_core_by_field"]["address"], 1)
        self.assertEqual(receipt["missing_core_by_field"]["birthday"], 1)

    def test_receipt_does_not_leak_contact_values(self):
        google = {
            "contacts": [
                g("Sensitive Person", "secret@example.com", "+1 416 555 9999"),
            ]
        }
        apple = {
            "containers": [
                {
                    "type": "carddav",
                    "contacts": [
                        a("Sensitive Person", "secret@example.com", "+14165559999")
                    ],
                }
            ]
        }
        receipt = MOD.verify(
            google, apple, min_coverage=1.0, max_core_field_loss_rate=0.0
        )
        serialized = json.dumps(receipt)
        self.assertNotIn("Sensitive Person", serialized)
        self.assertNotIn("secret@example.com", serialized)
        self.assertNotIn("4165559999", serialized)
        self.assertFalse(receipt["privacy"]["receipt_contains_names"])
        self.assertFalse(receipt["privacy"]["receipt_contains_provider_contact_ids"])


if __name__ == "__main__":
    unittest.main()
