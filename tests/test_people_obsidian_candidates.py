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
    name = "people_obsidian_candidates_test"
    spec = importlib.util.spec_from_file_location(
        name, SCRIPTS / "people_obsidian_candidates.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CANDIDATES = load_module()


def write_person(root: Path, folder: str, filename: str, aliases: str, heading: str) -> Path:
    path = root / "20 Areas" / "People" / folder / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\naliases: [{aliases}]\ntype: person\ntags: [person]\n---\n# {heading}\nprivate prose\n",
        encoding="utf-8",
    )
    return path


def write_google(path: Path, contacts):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "account_scope": "google-primary",
                "contacts": contacts,
            }
        ),
        encoding="utf-8",
    )


class CandidateProfileTests(unittest.TestCase):
    def test_scans_only_canonical_person_notes_and_skips_archive_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_person(root, "Taylor Example", "00 Taylor.md", "Taylor, Taylor Example", "Taylor")
            write_person(
                root,
                "ZZ_Archived/Old Person",
                "00 Old.md",
                "Old Person",
                "Old Person",
            )
            (root / "20 Areas" / "People" / "Taylor Example" / "Mentions — Taylor.md").write_text("x")

            profiles = CANDIDATES._canonical_profiles(
                root, Path("20 Areas/People"), include_archived=False
            )
            self.assertEqual(len(profiles), 1)
            self.assertIn("Taylor Example", profiles[0].names)

    def test_exact_name_candidate_is_review_only(self):
        profile = CANDIDATES.NoteProfile(
            path="20 Areas/People/Jane Doe/00 Jane.md",
            names=("Jane", "Jane Doe"),
            emails=(),
            phones=(),
        )
        contacts = [
            {
                "external_id": "people/c1",
                "display_name": "Jane Doe",
                "emails": [],
                "phones": [],
            }
        ]
        result = CANDIDATES._candidate_for_profile(profile, contacts, {})
        self.assertEqual(result[0]["match_mode"], "exact_name")
        self.assertIsNone(result[0]["person_id"])

    def test_middle_name_difference_is_separate_candidate_class(self):
        profile = CANDIDATES.NoteProfile(
            path="20 Areas/People/Taylor Mariah Smith/00 Taylor.md",
            names=("Taylor", "Taylor Mariah Smith"),
            emails=(),
            phones=(),
        )
        contacts = [
            {
                "external_id": "people/c2",
                "display_name": "Taylor Smith",
                "emails": [],
                "phones": [],
            }
        ]
        result = CANDIDATES._candidate_for_profile(profile, contacts, {})
        self.assertEqual(result[0]["match_mode"], "token_name")
        self.assertEqual(result[0]["score"], 0.92)

    def test_structured_email_beats_name_matching(self):
        profile = CANDIDATES.NoteProfile(
            path="20 Areas/People/Person/00 Person.md",
            names=("Different Name",),
            emails=("person@example.test",),
            phones=(),
        )
        contacts = [
            {
                "external_id": "people/c3",
                "display_name": "Actual Person",
                "emails": ["PERSON@example.test"],
                "phones": [],
            }
        ]
        result = CANDIDATES._candidate_for_profile(
            profile, contacts, {"people/c3": "00000000-0000-0000-0000-000000000003"}
        )
        self.assertEqual(result[0]["match_mode"], "strong_identifier")
        self.assertEqual(result[0]["score"], 1.0)


class CandidateReceiptTests(unittest.TestCase):
    def test_build_review_writes_nothing_and_receipt_is_aggregate_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = write_person(root, "Jane Doe", "00 Jane.md", "Jane, Jane Doe", "Jane")
            original = note.read_text(encoding="utf-8")
            snapshot = root / ".private" / "people" / "google.json"
            write_google(
                snapshot,
                [
                    {
                        "external_id": "people/c1",
                        "display_name": "Jane Doe",
                        "emails": ["jane@example.test"],
                        "phones": [],
                    }
                ],
            )

            review, receipt = CANDIDATES.build_review(
                vault_root=root,
                people_root=Path("20 Areas/People"),
                google_snapshot=snapshot,
                database_url=None,
                include_archived=False,
            )

            self.assertEqual(note.read_text(encoding="utf-8"), original)
            self.assertFalse(review["auto_apply_allowed"])
            self.assertEqual(receipt["frontmatter_writes"], 0)
            self.assertEqual(receipt["neon_writes"], 0)
            self.assertEqual(receipt["name_based_auto_links_created"], 0)
            serialized = json.dumps(receipt)
            self.assertNotIn("Jane", serialized)
            self.assertNotIn("jane@example.test", serialized)
            self.assertNotIn("people/c1", serialized)


if __name__ == "__main__":
    unittest.main()
