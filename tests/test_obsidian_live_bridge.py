import importlib.util
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


BRIDGE = load("obsidian_local_bridge", "scripts/obsidian_local_bridge.py")
IMPORTER = load("import_people_obsidian_refs", "scripts/import_people_obsidian_refs.py")
DISCOVER = load("people_obsidian_discover", "scripts/people_obsidian_discover.py")


class ObsidianBridgeSafetyTests(unittest.TestCase):
    def test_state_requires_long_token_and_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                BRIDGE.BridgeState(
                    vault_root=root,
                    vault_scope="primary",
                    token="short",
                    allowed_prefixes=("People",),
                    audit_path=root / "audit.jsonl",
                )

    def test_path_confinement_hidden_and_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "People").mkdir()
            (root / "People" / "One.md").write_text("hello")
            (root / ".obsidian").mkdir()
            (root / ".obsidian" / "Secret.md").write_text("secret")
            path, normalized = BRIDGE._safe_note(root, "People/One.md", ("People",))
            self.assertTrue(path.is_file())
            self.assertEqual(normalized, "People/One.md")
            with self.assertRaises(ValueError):
                BRIDGE._safe_note(root, ".obsidian/Secret.md", ("People",))
            with self.assertRaises(ValueError):
                BRIDGE._safe_note(root, "../outside.md", ("People",))

    def test_auth_uses_bearer_and_audit_has_no_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = root / "audit.jsonl"
            state = BRIDGE.BridgeState(
                vault_root=root,
                vault_scope="primary",
                token="x" * 32,
                allowed_prefixes=("People",),
                audit_path=audit,
            )
            self.assertTrue(state.authorized("Bearer " + "x" * 32))
            self.assertFalse(state.authorized("Bearer wrong"))
            state.audit(action="note_read", status="succeeded", normalized_path="People/Private.md")
            raw = audit.read_text()
            self.assertNotIn("People/Private.md", raw)
            self.assertIn('"content_recorded": false', raw)


class ObsidianRefPlanValidationTests(unittest.TestCase):
    def _plan(self):
        person = str(uuid.uuid4())
        note = str(uuid.uuid4())
        return {
            "schema_version": 1,
            "system_id": "obsidian",
            "account_scope": "primary-vault",
            "link_contract": "obsidian_frontmatter_v1",
            "refs": [
                {
                    "internal_type": "person",
                    "internal_id": person,
                    "system_id": "obsidian",
                    "account_scope": "primary-vault",
                    "external_id": f"note:{note}",
                    "ref_kind": "narrative",
                    "metadata": {"link_contract": "obsidian_frontmatter_v1"},
                }
            ],
        }

    def test_valid_plan_normalizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            path.write_text(json.dumps(self._plan()))
            result = IMPORTER.load_and_validate_plan(path)
            self.assertEqual(len(result["refs"]), 1)

    def test_rejects_private_metadata(self):
        plan = self._plan()
        plan["refs"][0]["metadata"]["note_path"] = "People/Private.md"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            path.write_text(json.dumps(plan))
            with self.assertRaises(ValueError):
                IMPORTER.load_and_validate_plan(path)

    def test_rejects_one_note_for_two_people(self):
        plan = self._plan()
        duplicate = dict(plan["refs"][0])
        duplicate["metadata"] = dict(duplicate["metadata"])
        duplicate["internal_id"] = str(uuid.uuid4())
        plan["refs"].append(duplicate)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            path.write_text(json.dumps(plan))
            with self.assertRaises(ValueError):
                IMPORTER.load_and_validate_plan(path)


class ObsidianExplicitDiscoveryTests(unittest.TestCase):
    def test_only_explicit_person_ids_are_discovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "People").mkdir()
            person = str(uuid.uuid4())
            (root / "People" / "Explicit.md").write_text(
                f'---\nllm4life_person_id: "{person}"\n---\nPrivate prose\n'
            )
            (root / "People" / "Name Only.md").write_text("# A Person Name\n")
            manifest, receipt = DISCOVER.discover(root, vault_scope="primary-vault")
            self.assertEqual(len(manifest["links"]), 1)
            self.assertEqual(receipt["explicit_people_links_found"], 1)
            self.assertEqual(receipt["name_based_matches_attempted"], 0)
            serialized = json.dumps(receipt)
            self.assertNotIn(person, serialized)
            self.assertNotIn("Explicit.md", serialized)
            self.assertNotIn("Private prose", serialized)

    def test_conflicting_duplicate_person_links_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            person = str(uuid.uuid4())
            (root / "One.md").write_text(f'---\nllm4life_person_id: "{person}"\n---\n')
            (root / "Two.md").write_text(f'---\nllm4life_person_id: "{person}"\n---\n')
            with self.assertRaises(ValueError):
                DISCOVER.discover(root, vault_scope="primary-vault")


if __name__ == "__main__":
    unittest.main()
