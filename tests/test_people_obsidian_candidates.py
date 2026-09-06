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
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / "people_obsidian_candidates.py")
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
    def test_archived_canonical_people_are_included_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_person(root, "Taylor Example", "00 Taylor.md", "Taylor, Taylor Example", "Taylor")
            write_person(root, "ZZ_Archived/Old Person", "00 Old.md", "Old Person", "Old Person")
            profiles = CANDIDATES._person_sources(root, Path("20 Areas/People"), include_archived=True)
            self.assertEqual({p.source_kind for p in profiles}, {"active_profile", "archived_profile"})

    def test_archive_can_still_be_excluded_explicitly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_person(root, "Taylor Example", "00 Taylor.md", "Taylor, Taylor Example", "Taylor")
            write_person(root, "ZZ_Archived/Old Person", "00 Old.md", "Old Person", "Old Person")
            profiles = CANDIDATES._person_sources(root, Path("20 Areas/People"), include_archived=False)
            self.assertEqual(len(profiles), 1)
            self.assertEqual(profiles[0].source_kind, "active_profile")

    def test_legacy_archived_folder_without_00_profile_is_discovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "20 Areas" / "People" / "ZZ_Archived" / "Legacy Person 1"
            folder.mkdir(parents=True)
            (folder / "Interests.md").write_text("private", encoding="utf-8")
            (folder / "Personality.md").write_text("private", encoding="utf-8")
            profiles = CANDIDATES._person_sources(root, Path("20 Areas/People"), include_archived=True)
            self.assertEqual(len(profiles), 1)
            self.assertEqual(profiles[0].source_kind, "archived_legacy_folder")
            self.assertIn("Legacy Person", profiles[0].names)
            self.assertEqual(len(profiles[0].mapping_note_paths), 2)

    def test_moc_only_archive_container_is_not_a_person(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "20 Areas" / "People" / "ZZ_Archived" / "Women"
            folder.mkdir(parents=True)
            (folder / "_Women MOC.md").write_text("# Index\n", encoding="utf-8")
            profiles = CANDIDATES._person_sources(root, Path("20 Areas/People"), include_archived=True)
            self.assertEqual(profiles, [])

    def test_exact_name_candidate_is_review_only(self):
        profile = CANDIDATES.NoteProfile(
            path="20 Areas/People/Jane Doe/00 Jane.md",
            names=("Jane", "Jane Doe"),
            emails=(),
            phones=(),
        )
        contacts = [{"external_id": "people/c1", "display_name": "Jane Doe", "emails": [], "phones": []}]
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
        contacts = [{"external_id": "people/c2", "display_name": "Taylor Smith", "emails": [], "phones": []}]
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
        contacts = [{"external_id": "people/c3", "display_name": "Actual Person", "emails": ["PERSON@example.test"], "phones": []}]
        result = CANDIDATES._candidate_for_profile(
            profile, contacts, {"people/c3": "00000000-0000-0000-0000-000000000003"}
        )
        self.assertEqual(result[0]["match_mode"], "strong_identifier")
        self.assertEqual(result[0]["score"], 1.0)


class DiaryEvidenceTests(unittest.TestCase):
    def test_diary_is_evidence_not_person_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_person(root, "Jane Doe", "00 Jane.md", "Jane Doe", "Jane Doe")
            diary = root / "20 Areas" / "People" / "Zubair" / "Journal Entries" / "2025" / "2025-01-02.md"
            diary.parent.mkdir(parents=True)
            diary.write_text("---\nsource: imported_diary_text\ndate: 2025-01-02\n---\nSaw [[Jane Doe]].", encoding="utf-8")
            profiles = CANDIDATES._person_sources(root, Path("20 Areas/People"), include_archived=True)
            evidence, counts = CANDIDATES._diary_evidence(root, Path("20 Areas/People"), profiles)
            self.assertEqual(len(profiles), 1)
            self.assertEqual(len(evidence), 1)
            self.assertEqual(evidence[0]["source_kind"], "imported_diary_text")
            self.assertFalse(evidence[0]["raw_narrative_copied"])
            self.assertEqual(len(evidence[0]["explicit_person_sources"]), 1)
            self.assertEqual(counts["diary_sources_scanned"], 1)
            self.assertNotIn("Saw", json.dumps(evidence))

    def test_unique_plain_name_mention_is_review_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_person(root, "Taylor Smith", "00 Taylor.md", "Taylor Smith", "Taylor Smith")
            diary = root / "20 Areas" / "People" / "Zubair" / "Journal Entries" / "2025" / "2025-02-03.md"
            diary.parent.mkdir(parents=True)
            diary.write_text("Met Taylor Smith for coffee.", encoding="utf-8")
            profiles = CANDIDATES._person_sources(root, Path("20 Areas/People"), include_archived=True)
            evidence, _ = CANDIDATES._diary_evidence(root, Path("20 Areas/People"), profiles)
            self.assertEqual(len(evidence), 1)
            self.assertEqual(evidence[0]["mention_candidates"][0]["resolution"], "review_required")

    def test_ambiguous_same_name_plain_mention_is_not_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_person(root, "Alex One", "00 Alex One.md", "Alex", "Alex One")
            write_person(root, "Alex Two", "00 Alex Two.md", "Alex", "Alex Two")
            diary = root / "20 Areas" / "People" / "Zubair" / "Journal Entries" / "2025" / "2025-02-04.md"
            diary.parent.mkdir(parents=True)
            diary.write_text("Alex called.", encoding="utf-8")
            profiles = CANDIDATES._person_sources(root, Path("20 Areas/People"), include_archived=True)
            evidence, counts = CANDIDATES._diary_evidence(root, Path("20 Areas/People"), profiles)
            self.assertEqual(len(evidence), 0)
            self.assertGreater(counts["diary_ambiguous_alias_mentions"], 0)


class CandidateReceiptTests(unittest.TestCase):
    def test_build_review_writes_nothing_and_receipt_is_aggregate_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            note = write_person(root, "Jane Doe", "00 Jane.md", "Jane, Jane Doe", "Jane")
            original = note.read_text(encoding="utf-8")
            diary = root / "20 Areas" / "People" / "Zubair" / "Journal Entries" / "2025" / "2025-03-04.md"
            diary.parent.mkdir(parents=True)
            diary.write_text("Jane private diary sentence.", encoding="utf-8")
            snapshot = root / ".private" / "people" / "google.json"
            write_google(snapshot, [{"external_id": "people/c1", "display_name": "Jane Doe", "emails": ["jane@example.test"], "phones": []}])

            review, receipt = CANDIDATES.build_review(
                vault_root=root,
                people_root=Path("20 Areas/People"),
                google_snapshot=snapshot,
                database_url=None,
                include_archived=True,
                include_diary_sources=True,
            )

            self.assertEqual(note.read_text(encoding="utf-8"), original)
            self.assertFalse(review["auto_apply_allowed"])
            self.assertFalse(review["diary_policy"]["diary_notes_are_people"])
            self.assertEqual(receipt["frontmatter_writes"], 0)
            self.assertEqual(receipt["neon_writes"], 0)
            self.assertEqual(receipt["name_based_auto_links_created"], 0)
            self.assertEqual(receipt["diary_fact_auto_writes"], 0)
            serialized = json.dumps(receipt)
            for private_value in ("Jane", "jane@example.test", "people/c1", "2025-03-04.md", "private diary sentence"):
                self.assertNotIn(private_value, serialized)

    def test_existing_manifest_is_reused_instead_of_overwritten_by_review(self):
        review = {
            "vault_scope": "primary-vault",
            "entries": [{
                "source_path": "20 Areas/People/New/00 New.md",
                "source_kind": "active_profile",
                "mapping_note_paths": ["20 Areas/People/New/00 New.md"],
                "decision": "already_mapped",
                "candidates": [],
            }],
        }
        existing = {
            "vault_scope": "primary-vault",
            "links": [{
                "person_id": "00000000-0000-0000-0000-000000000001",
                "note_path": "20 Areas/People/Existing/00 Existing.md",
            }],
        }
        merged = CANDIDATES._interactive_approve(review, existing)
        self.assertEqual(len(merged["links"]), 1)
        self.assertEqual(merged["links"][0]["note_path"], "20 Areas/People/Existing/00 Existing.md")


if __name__ == "__main__":
    unittest.main()
