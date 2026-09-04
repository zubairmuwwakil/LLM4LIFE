import importlib.util
import json
import tempfile
import unittest
import uuid
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "people_obsidian_link.py"
SPEC = importlib.util.spec_from_file_location("people_obsidian_link", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MOD)


class PeopleObsidianLinkTests(unittest.TestCase):
    def test_adds_managed_frontmatter_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "People" / "Example.md"
            note.parent.mkdir()
            note.write_text("# Example\nNarrative stays here.\n")
            person_id = str(uuid.uuid4())
            manifest = {
                "vault_scope": "primary",
                "links": [{"person_id": person_id, "note_path": "People/Example.md"}],
            }

            plan, receipt = MOD.build_link_plan(
                vault_root=vault, manifest=manifest, apply_frontmatter=True
            )
            text = note.read_text()
            self.assertIn(f'{MOD.PERSON_KEY}: "{person_id}"', text)
            self.assertIn(MOD.NOTE_KEY, text)
            self.assertIn("Narrative stays here.", text)
            self.assertEqual(receipt["refs_planned"], 1)
            self.assertEqual(receipt["notes_changed_or_would_change"], 1)
            self.assertEqual(plan["refs"][0]["internal_id"], person_id)
            self.assertNotIn("People/Example.md", json.dumps(plan))

            plan2, receipt2 = MOD.build_link_plan(
                vault_root=vault, manifest=manifest, apply_frontmatter=True
            )
            self.assertEqual(receipt2["notes_already_linked"], 1)
            self.assertEqual(plan["refs"][0]["external_id"], plan2["refs"][0]["external_id"])

    def test_preserves_existing_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "Friend.md"
            note.write_text("---\ntags: [people]\n---\n# Friend\n")
            person_id = str(uuid.uuid4())
            manifest = {
                "vault_scope": "primary",
                "links": [{"person_id": person_id, "note_path": "Friend.md"}],
            }
            MOD.build_link_plan(vault_root=vault, manifest=manifest, apply_frontmatter=True)
            text = note.read_text()
            self.assertIn("tags: [people]", text)
            self.assertIn(MOD.PERSON_KEY, text)
            self.assertIn(MOD.NOTE_KEY, text)

    def test_rejects_conflicting_existing_person_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "Friend.md"
            existing = str(uuid.uuid4())
            requested = str(uuid.uuid4())
            note.write_text(f'---\n{MOD.PERSON_KEY}: "{existing}"\n---\n# Friend\n')
            manifest = {
                "vault_scope": "primary",
                "links": [{"person_id": requested, "note_path": "Friend.md"}],
            }
            with self.assertRaisesRegex(ValueError, "conflicts"):
                MOD.build_link_plan(vault_root=vault, manifest=manifest, apply_frontmatter=True)
            self.assertIn(existing, note.read_text())

    def test_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            outside = Path(tmp) / "outside.md"
            outside.write_text("# Outside\n")
            manifest = {
                "vault_scope": "primary",
                "links": [{"person_id": str(uuid.uuid4()), "note_path": "../outside.md"}],
            }
            with self.assertRaisesRegex(ValueError, "escapes"):
                MOD.build_link_plan(vault_root=vault, manifest=manifest, apply_frontmatter=False)

    def test_aggregate_receipt_contains_no_private_link_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "Private Person.md"
            note.write_text("# Private narrative text\n")
            person_id = str(uuid.uuid4())
            manifest = {
                "vault_scope": "primary",
                "links": [{"person_id": person_id, "note_path": "Private Person.md"}],
            }
            _, receipt = MOD.build_link_plan(
                vault_root=vault, manifest=manifest, apply_frontmatter=False
            )
            serialized = json.dumps(receipt)
            self.assertNotIn(person_id, serialized)
            self.assertNotIn("Private Person.md", serialized)
            self.assertNotIn("Private narrative text", serialized)
            self.assertFalse(receipt["privacy"]["receipt_contains_person_ids"])
            self.assertFalse(receipt["privacy"]["receipt_contains_note_paths"])
            self.assertFalse(receipt["privacy"]["receipt_contains_narrative"])


if __name__ == "__main__":
    unittest.main()
