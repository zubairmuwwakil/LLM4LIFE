from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from people_dedup import (  # noqa: E402
    generate_candidates,
    load_inventory,
    normalize_email,
    normalize_phone,
    resolve_exact_provider_ref,
)


class PeopleDedupTests(unittest.TestCase):
    def _record(self, **overrides):
        raw = {
            "source": "google_contacts",
            "account_scope": "acct-a",
            "external_id": "people/a",
            "display_name": "Alex Example",
            "emails": [],
            "phones": [],
            "archived": False,
        }
        raw.update(overrides)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventory.json"
            path.write_text(json.dumps([raw]), encoding="utf-8")
            return load_inventory(path)[0]

    def test_same_name_different_person_is_never_high_confidence(self):
        a = self._record(external_id="people/a")
        b = self._record(source="apple_contacts", external_id="apple/b")
        candidates = generate_candidates([a, b], include_name_only=True)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["confidence_band"], "weak")
        self.assertFalse(candidates[0]["automatic_merge"])

    def test_renamed_contact_same_provider_ref_resolves_before_field_matching(self):
        original = self._record(external_id="people/a", display_name="Alex Example")
        renamed = self._record(external_id="people/a", display_name="Alex Renamed")
        mapping = {original.source_key: "00000000-0000-0000-0000-000000000001"}
        self.assertEqual(resolve_exact_provider_ref(renamed, mapping), mapping[original.source_key])

    def test_same_snapshot_duplicate_provider_ref_requires_identical_payload(self):
        rows = [
            {
                "source": "google_contacts",
                "account_scope": "acct-a",
                "external_id": "people/a",
                "display_name": "Alex Example",
                "emails": ["alex@example.com"],
                "phones": [],
            },
            {
                "source": "google_contacts",
                "account_scope": "acct-a",
                "external_id": "people/a",
                "display_name": "Alex Example",
                "emails": ["alex@example.com"],
                "phones": [],
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventory.json"
            path.write_text(json.dumps(rows), encoding="utf-8")
            self.assertEqual(len(load_inventory(path)), 1)

        rows[1]["display_name"] = "Alex Renamed"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventory.json"
            path.write_text(json.dumps(rows), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "conflicting rerun rows"):
                load_inventory(path)

    def test_same_email_with_conflicting_name_is_manual_conflict(self):
        a = self._record(external_id="people/a", emails=["Shared@Example.com"], display_name="Alex Example")
        b = self._record(
            source="apple_contacts",
            external_id="apple/b",
            emails=["shared@example.com"],
            display_name="Jordan Example",
        )
        candidate = generate_candidates([a, b])[0]
        self.assertEqual(candidate["confidence_band"], "conflict")
        self.assertIn("strong_contact_point_with_conflicting_name", candidate["reasons"])

    def test_email_plus_phone_is_high_but_still_not_auto_merge(self):
        a = self._record(external_id="people/a", emails=["alex@example.com"], phones=["416-555-0100"])
        b = self._record(
            source="apple_contacts",
            external_id="apple/b",
            emails=["ALEX@example.com"],
            phones=["+1 (416) 555-0100"],
        )
        candidate = generate_candidates([a, b])[0]
        self.assertEqual(candidate["confidence_band"], "high")
        self.assertFalse(candidate["automatic_merge"])

    def test_archived_record_is_preserved_in_candidate_metadata(self):
        a = self._record(external_id="people/a", emails=["alex@example.com"])
        b = self._record(
            source="apple_contacts",
            external_id="apple/b",
            emails=["alex@example.com"],
            archived=True,
        )
        candidate = generate_candidates([a, b])[0]
        self.assertIn("archived_source_record", candidate["reasons"])

    def test_candidate_ids_are_idempotent_across_reruns_and_input_order(self):
        a = self._record(external_id="people/a", emails=["alex@example.com"], phones=["4165550100"])
        b = self._record(
            source="apple_contacts",
            external_id="apple/b",
            emails=["alex@example.com"],
            phones=["+14165550100"],
        )
        first = generate_candidates([a, b])
        second = generate_candidates([b, a])
        self.assertEqual(first, second)

    def test_normalization_is_conservative(self):
        self.assertEqual(normalize_email("  ALEX@EXAMPLE.COM "), "alex@example.com")
        self.assertEqual(normalize_phone("(416) 555-0100"), ("+14165550100", True))
        self.assertEqual(normalize_phone("555-0100"), ("5550100", False))


if __name__ == "__main__":
    unittest.main()
