import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'


def load_module():
    sys.path.insert(0, str(SCRIPTS))
    name = 'people_structured_memory_review_test'
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / 'people_structured_memory_review.py')
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MOD = load_module()
ALICE = '00000000-0000-0000-0000-000000000001'
BOB = '00000000-0000-0000-0000-000000000002'


class StructuredMemoryReviewTests(unittest.TestCase):
    def _fixture(self, root: Path):
        people = root / '20 Areas' / 'People'
        alice_dir = people / 'Alice Example'
        bob_dir = people / 'Bob Example'
        alice_dir.mkdir(parents=True)
        bob_dir.mkdir(parents=True)
        (alice_dir / '00 Alice.md').write_text(
            '---\naliases: [Alice, Alice Example]\ntype: person\n---\n# Alice\n\nBirthday: Apr 5\n- sister: [[Bob Example]]\n- mother: Jane Unknown\n',
            encoding='utf-8',
        )
        (bob_dir / '00 Bob.md').write_text(
            '---\naliases: [Bob, Bob Example]\ntype: person\n---\n# Bob\n',
            encoding='utf-8',
        )
        (people / 'Timeline.md').write_text('**2021-04-05** — Alice birthday\n', encoding='utf-8')

        review = {
            'schema_version': 2,
            'entries': [
                {'source_path': '20 Areas/People/Alice Example/00 Alice.md', 'mapping_note_paths': ['20 Areas/People/Alice Example/00 Alice.md'], 'note_names': ['Alice', 'Alice Example'], 'existing_person_id': ALICE},
                {'source_path': '20 Areas/People/Bob Example/00 Bob.md', 'mapping_note_paths': ['20 Areas/People/Bob Example/00 Bob.md'], 'note_names': ['Bob', 'Bob Example'], 'existing_person_id': BOB},
            ],
        }
        review_path = root / 'candidate.json'
        manifest_path = root / 'manifest.json'
        review_path.write_text(json.dumps(review), encoding='utf-8')
        manifest_path.write_text(json.dumps({'links': []}), encoding='utf-8')
        return review_path, manifest_path

    def test_build_finds_dates_resolved_edges_and_holds_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            review_path, manifest_path = self._fixture(root)
            review, receipt = MOD.build_review(
                vault_root=root,
                candidate_review_path=review_path,
                manifest_path=manifest_path,
                roots=(Path('20 Areas/People'),),
            )
            self.assertGreaterEqual(len(review['date_candidates']), 2)
            birthdays = [c for c in review['date_candidates'] if c['date_type'] == 'birthday']
            self.assertTrue(any(c['person_id'] == ALICE and c['month'] == 4 and c['day'] == 5 for c in birthdays))
            self.assertTrue(all(c['year'] is None for c in birthdays))
            resolved = [c for c in review['relationship_candidates'] if c.get('resolution') == 'two_resolved_people']
            self.assertTrue(any(c['relationship_type'] == 'sibling' for c in resolved))
            held = [c for c in review['relationship_candidates'] if c.get('resolution') == 'unresolved_target']
            self.assertTrue(any(c.get('unresolved_target_name') == 'Jane Unknown' for c in held))
            self.assertEqual(receipt['neon_writes'], 0)
            self.assertEqual(receipt['obsidian_writes'], 0)

    def test_validate_only_promotes_approved_resolved_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            review_path, manifest_path = self._fixture(root)
            review, _ = MOD.build_review(
                vault_root=root,
                candidate_review_path=review_path,
                manifest_path=manifest_path,
                roots=(Path('20 Areas/People'),),
            )
            date = next(c for c in review['date_candidates'] if c['person_id'] == ALICE)
            edge = next(c for c in review['relationship_candidates'] if c.get('resolution') == 'two_resolved_people')
            date['approved'] = True
            edge['approved'] = True
            reviewed_path = root / 'reviewed.json'
            reviewed_path.write_text(json.dumps(review), encoding='utf-8')
            plan, receipt = MOD.validate_reviewed(reviewed_path)
            self.assertEqual(len(plan['proposals']), 2)
            self.assertEqual(receipt['approved_person_dates'], 1)
            self.assertEqual(receipt['approved_relationship_edges'], 1)
            self.assertFalse(plan['apply_allowed'])
            serialized = json.dumps(plan)
            self.assertNotIn('evidence_line', serialized)
            self.assertNotIn('source_note', serialized)


if __name__ == '__main__':
    unittest.main()
