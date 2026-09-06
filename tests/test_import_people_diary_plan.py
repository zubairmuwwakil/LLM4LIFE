import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_module():
    sys.path.insert(0, str(SCRIPTS))
    name = "import_people_diary_plan_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / "import_people_diary_plan.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


IMPORTER = load_module()

PERSON = "00000000-0000-0000-0000-000000000001"
SOURCE_SHA = "a" * 64


def base_plan():
    return {
        "schema_version": 1,
        "private_artifact": True,
        "apply_allowed": False,
        "items": [
            {
                "source_note": "20 Areas/People/Example/Journal Entries/2025/2025-01-02.md",
                "source_date": "2025-01-02",
                "source_sha256": SOURCE_SHA,
                "proposals": [
                    {
                        "proposal_type": "fact",
                        "person_id": PERSON,
                        "fact_key": "interests.example",
                        "value": ["A", "B"],
                        "source_kind": "user_edited_import",
                        "source_system_id": "obsidian",
                        "asserted_on": "2025-01-02",
                        "confidence": 1.0,
                        "sensitivity_class": "standard",
                    },
                    {
                        "proposal_type": "interaction",
                        "person_ids": [PERSON],
                        "interaction_type": "met_in_person",
                        "occurred_on": "2025-01-02",
                        "summary": "Met for coffee.",
                        "source_kind": "interaction_import",
                        "source_system_id": "obsidian",
                        "sensitivity_class": "standard",
                    },
                ],
            }
        ],
        "policy": {
            "requires_separate_apply_authorization": True,
            "raw_diary_prose_in_plan": False,
            "model_suggestion_source_kind_allowed": False,
            "sensitive_auto_persist_allowed": False,
        },
    }


class PlanNormalizationTests(unittest.TestCase):
    def test_deterministic_ids_are_stable_and_ignore_note_path(self):
        first = base_plan()
        second = base_plan()
        second["items"][0]["source_note"] = "Moved/Elsewhere.md"
        facts1, interactions1 = IMPORTER.normalize_plan(first)
        facts2, interactions2 = IMPORTER.normalize_plan(second)
        self.assertEqual(facts1[0].id, facts2[0].id)
        self.assertEqual(interactions1[0].id, interactions2[0].id)
        self.assertEqual(interactions1[0].interaction_key, interactions2[0].interaction_key)

    def test_fact_value_change_changes_deterministic_id(self):
        first = base_plan()
        second = base_plan()
        second["items"][0]["proposals"][0]["value"] = ["A", "C"]
        facts1, _ = IMPORTER.normalize_plan(first)
        facts2, _ = IMPORTER.normalize_plan(second)
        self.assertNotEqual(facts1[0].id, facts2[0].id)

    def test_sensitive_proposal_is_refused(self):
        plan = base_plan()
        plan["items"][0]["proposals"][0]["sensitivity_class"] = "sensitive"
        with self.assertRaisesRegex(ValueError, "refuses sensitive"):
            IMPORTER.normalize_plan(plan)

    def test_fact_date_must_match_source_date(self):
        plan = base_plan()
        plan["items"][0]["proposals"][0]["asserted_on"] = "2025-01-03"
        with self.assertRaisesRegex(ValueError, "must match"):
            IMPORTER.normalize_plan(plan)

    def test_interaction_date_must_match_source_date(self):
        plan = base_plan()
        plan["items"][0]["proposals"][1]["occurred_on"] = "2025-01-03"
        with self.assertRaisesRegex(ValueError, "must match"):
            IMPORTER.normalize_plan(plan)

    def test_plan_policy_gate_must_remain_enabled(self):
        plan = base_plan()
        plan["policy"]["requires_separate_apply_authorization"] = False
        with self.assertRaisesRegex(ValueError, "separate-authorization"):
            IMPORTER.normalize_plan(plan)

    def test_raw_narrative_policy_cannot_be_enabled(self):
        plan = base_plan()
        plan["policy"]["raw_diary_prose_in_plan"] = True
        with self.assertRaisesRegex(ValueError, "raw narrative"):
            IMPORTER.normalize_plan(plan)

    def test_normalized_operations_do_not_contain_note_paths_or_raw_prose(self):
        facts, interactions = IMPORTER.normalize_plan(base_plan())
        serialized = json.dumps(
            {
                "facts": [fact.__dict__ for fact in facts],
                "interactions": [interaction.__dict__ for interaction in interactions],
            },
            default=str,
        )
        self.assertNotIn("Journal Entries", serialized)
        self.assertNotIn("source_note", serialized)
        self.assertNotIn("raw_narrative", serialized)


class ReceiptTests(unittest.TestCase):
    def test_receipt_path_can_stay_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".private" / "people" / "receipt.json"
            IMPORTER._write_receipt(
                path,
                {
                    "schema_version": 1,
                    "facts_planned": 1,
                    "privacy": {
                        "receipt_contains_names": False,
                        "receipt_contains_person_ids": False,
                        "receipt_contains_note_paths": False,
                        "receipt_contains_diary_prose": False,
                        "receipt_contains_fact_values": False,
                    },
                },
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["facts_planned"], 1)
            self.assertFalse(payload["privacy"]["receipt_contains_note_paths"])


if __name__ == "__main__":
    unittest.main()
