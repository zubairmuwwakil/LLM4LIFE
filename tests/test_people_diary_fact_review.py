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
    name = "people_diary_fact_review_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / "people_diary_fact_review.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


REVIEW = load_module()
PERSON_ID = "00000000-0000-0000-0000-000000000001"
OTHER_ID = "00000000-0000-0000-0000-000000000002"


class DiaryBatchTests(unittest.TestCase):
    def test_batch_keeps_raw_narrative_private_and_receipt_aggregate_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            diary = root / "20 Areas" / "People" / "Zubair" / "Journal Entries" / "2025" / "2025-01-02.md"
            diary.parent.mkdir(parents=True)
            diary.write_text(
                "---\nsource: imported_diary_text\ndate: 2025-01-02\n---\nPrivate sentence about Jane.",
                encoding="utf-8",
            )
            candidate_review = root / ".private" / "people" / "obsidian_candidate_review.json"
            candidate_review.parent.mkdir(parents=True)
            candidate_review.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "diary_evidence": [
                            {
                                "source_note": diary.relative_to(root).as_posix(),
                                "source_date": "2025-01-02",
                                "source_kind": "imported_diary_text",
                                "explicit_person_sources": [
                                    {
                                        "person_source_path": "20 Areas/People/Jane/00 Jane.md",
                                        "person_id": PERSON_ID,
                                    }
                                ],
                                "mention_candidates": [],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            batch, receipt = REVIEW.build_batch(
                vault_root=root,
                candidate_review_path=candidate_review,
                offset=0,
                batch_size=25,
            )

            self.assertEqual(len(batch["items"]), 1)
            self.assertIn("Private sentence", batch["items"][0]["raw_narrative"])
            self.assertEqual(batch["items"][0]["resolved_people"][0]["person_id"], PERSON_ID)
            serialized_receipt = json.dumps(receipt)
            self.assertNotIn("Private sentence", serialized_receipt)
            self.assertNotIn("Jane", serialized_receipt)
            self.assertNotIn(PERSON_ID, serialized_receipt)
            self.assertNotIn("2025-01-02.md", serialized_receipt)
            self.assertEqual(receipt["neon_writes"], 0)
            self.assertEqual(receipt["obsidian_writes"], 0)

    def test_plain_name_only_person_is_not_eligible_for_fact_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            diary = root / "20 Areas" / "People" / "Zubair" / "Journal Entries" / "2025" / "2025-01-03.md"
            diary.parent.mkdir(parents=True)
            diary.write_text("Jane called.", encoding="utf-8")
            candidate_review = root / "candidate.json"
            candidate_review.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "diary_evidence": [
                            {
                                "source_note": diary.relative_to(root).as_posix(),
                                "source_date": "2025-01-03",
                                "explicit_person_sources": [],
                                "mention_candidates": [
                                    {
                                        "person_source_path": "20 Areas/People/Jane/00 Jane.md",
                                        "person_id": PERSON_ID,
                                        "resolution": "review_required",
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            batch, receipt = REVIEW.build_batch(
                vault_root=root,
                candidate_review_path=candidate_review,
                offset=0,
                batch_size=25,
            )
            self.assertEqual(batch["items"], [])
            self.assertEqual(receipt["skipped_without_resolved_people"], 1)


class DiaryPlanTests(unittest.TestCase):
    def test_validated_plan_removes_raw_diary_prose_and_never_allows_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            reviewed = Path(tmp) / "reviewed.json"
            reviewed.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "source_note": "20 Areas/People/Zubair/Journal Entries/2025/2025-01-02.md",
                                "source_date": "2025-01-02",
                                "source_sha256": "a" * 64,
                                "resolved_people": [{"person_id": PERSON_ID}],
                                "raw_narrative": "Private source text that must not enter plan.",
                                "proposals": [
                                    {
                                        "proposal_type": "fact",
                                        "person_id": PERSON_ID,
                                        "fact_key": "likes.coffee",
                                        "value": True,
                                        "sensitivity_class": "standard",
                                        "evidence_basis": "explicit_user_statement",
                                        "approved": True,
                                    },
                                    {
                                        "proposal_type": "interaction",
                                        "person_ids": [PERSON_ID],
                                        "interaction_type": "met_in_person",
                                        "occurred_on": "2025-01-02",
                                        "summary": "Met for coffee",
                                        "sensitivity_class": "standard",
                                        "evidence_basis": "explicit_user_statement",
                                        "approved": True,
                                    },
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            plan, receipt = REVIEW.validate_reviewed(reviewed)
            serialized_plan = json.dumps(plan)
            self.assertFalse(plan["apply_allowed"])
            self.assertNotIn("Private source text", serialized_plan)
            self.assertEqual(plan["items"][0]["proposals"][0]["source_kind"], "user_edited_import")
            self.assertEqual(plan["items"][0]["proposals"][1]["source_kind"], "interaction_import")
            self.assertEqual(receipt["approved_fact_proposals"], 1)
            self.assertEqual(receipt["approved_interaction_proposals"], 1)
            self.assertEqual(receipt["neon_writes"], 0)

    def test_unknown_person_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            reviewed = Path(tmp) / "reviewed.json"
            reviewed.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "source_note": "journal.md",
                                "source_date": "2025-01-02",
                                "source_sha256": "b" * 64,
                                "resolved_people": [{"person_id": PERSON_ID}],
                                "proposals": [
                                    {
                                        "proposal_type": "fact",
                                        "person_id": OTHER_ID,
                                        "fact_key": "likes.coffee",
                                        "value": True,
                                        "sensitivity_class": "standard",
                                        "evidence_basis": "explicit_user_statement",
                                        "approved": True,
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "unknown person_id"):
                REVIEW.validate_reviewed(reviewed)

    def test_sensitive_fact_can_be_reviewed_but_is_not_silently_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            reviewed = Path(tmp) / "reviewed.json"
            reviewed.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "source_note": "journal.md",
                                "source_date": "2025-01-02",
                                "source_sha256": "c" * 64,
                                "resolved_people": [{"person_id": PERSON_ID}],
                                "proposals": [
                                    {
                                        "proposal_type": "fact",
                                        "person_id": PERSON_ID,
                                        "fact_key": "private.explicit_fact",
                                        "value": "reviewed",
                                        "sensitivity_class": "sensitive",
                                        "evidence_basis": "explicit_user_statement",
                                        "approved": True,
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            plan, receipt = REVIEW.validate_reviewed(reviewed)
            self.assertEqual(receipt["approved_sensitive_proposals"], 1)
            self.assertFalse(plan["policy"]["sensitive_auto_persist_allowed"])
            self.assertTrue(plan["policy"]["requires_separate_apply_authorization"])


if __name__ == "__main__":
    unittest.main()
