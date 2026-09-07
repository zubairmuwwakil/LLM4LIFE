import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))

import people_structured_memory_review as BASE


def load_profile_module():
    name = 'people_profile_relationship_review_test'
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / 'people_profile_relationship_review.py')
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MOD = load_profile_module()
ALICE = '00000000-0000-0000-0000-000000000001'
BOB = '00000000-0000-0000-0000-000000000002'
CAROL = '00000000-0000-0000-0000-000000000003'
GRANDMA = '00000000-0000-0000-0000-000000000004'


class ProfileRelationshipReviewTests(unittest.TestCase):
    def _fixture(self, root: Path):
        people = root / '20 Areas' / 'People'
        alice_dir = people / 'Alice Example'
        bob_dir = people / 'Bob Example'
        carol_dir = people / 'Carol Example'
        alice_dir.mkdir(parents=True)
        bob_dir.mkdir(parents=True)
        carol_dir.mkdir(parents=True)

        (alice_dir / '00 Alice.md').write_text(
            '# Alice\n\nFamily & Friends\n\n'
            'Bob Example (closer friend)\n'
            'Jane Unknown (mom)\n'
            '[[20 Areas/People/Carol Example/00 Carol.md|Carol]] (cousin)\n'
            '[[Local Grandma]] (grandma)\n\n'
            'Things Alice likes\n'
            'Something Else (friend)\n',
            encoding='utf-8',
        )
        (alice_dir / 'Local Grandma.md').write_text('# Grandma\n', encoding='utf-8')
        (bob_dir / '00 Bob.md').write_text('# Bob\n', encoding='utf-8')
        (carol_dir / '00 Carol.md').write_text('# Carol\n', encoding='utf-8')

        candidate = {
            'schema_version': 2,
            'entries': [
                {
                    'source_path': '20 Areas/People/Alice Example/00 Alice.md',
                    'mapping_note_paths': ['20 Areas/People/Alice Example/00 Alice.md'],
                    'note_names': ['Alice', 'Alice Example'],
                    'existing_person_id': ALICE,
                },
                {
                    'source_path': '20 Areas/People/Bob Example/00 Bob.md',
                    'mapping_note_paths': ['20 Areas/People/Bob Example/00 Bob.md'],
                    'note_names': ['Bob', 'Bob Example'],
                    'existing_person_id': BOB,
                },
                {
                    'source_path': '20 Areas/People/Carol Example/00 Carol.md',
                    'mapping_note_paths': ['20 Areas/People/Carol Example/00 Carol.md'],
                    'note_names': ['Carol', 'Carol Example'],
                    'existing_person_id': CAROL,
                },
                {
                    'source_path': '20 Areas/People/Alice Example/Local Grandma.md',
                    'mapping_note_paths': ['20 Areas/People/Alice Example/Local Grandma.md'],
                    'note_names': ['Local Grandma'],
                    'existing_person_id': GRANDMA,
                },
            ],
        }
        candidate_path = root / 'candidate.json'
        manifest_path = root / 'manifest.json'
        candidate_path.write_text(json.dumps(candidate), encoding='utf-8')
        manifest_path.write_text(json.dumps({'links': []}), encoding='utf-8')

        review, _ = BASE.build_review(
            vault_root=root,
            candidate_review_path=candidate_path,
            manifest_path=manifest_path,
            roots=(Path('20 Areas/People'),),
        )
        review_path = root / 'structured_review.json'
        review_path.write_text(json.dumps(review), encoding='utf-8')
        return candidate_path, manifest_path, review_path

    def test_family_friend_section_parses_resolved_and_held_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_path, manifest_path, review_path = self._fixture(root)
            review, receipt, added = MOD.enrich_review(
                vault_root=root,
                review_path=review_path,
                candidate_review_path=candidate_path,
                manifest_path=manifest_path,
            )

            self.assertEqual(receipt['family_friend_sections_found'], 1)
            self.assertEqual(receipt['resolved_relationship_candidates_added'], 3)
            self.assertEqual(receipt['held_unresolved_relationship_candidates_added'], 1)
            self.assertEqual(receipt['exact_wikilink_resolutions'], 2)
            self.assertEqual(receipt['unique_alias_resolutions'], 1)
            self.assertEqual(receipt['neon_writes'], 0)
            self.assertEqual(receipt['obsidian_writes'], 0)

            resolved = [c for c in added if c.get('resolution') == 'two_resolved_people']
            held = [c for c in added if c.get('resolution') == 'unresolved_target']

            self.assertTrue(any(
                c['source_person_id'] == ALICE and c['target_person_id'] == BOB and c['relationship_type'] == 'friend'
                for c in resolved
            ))
            self.assertTrue(any(
                c['source_person_id'] == ALICE and c['target_person_id'] == CAROL and c['relationship_type'] == 'cousin'
                for c in resolved
            ))
            self.assertTrue(any(
                c['source_person_id'] == GRANDMA and c['target_person_id'] == ALICE and c['relationship_type'] == 'grandparent'
                for c in resolved
            ))
            self.assertTrue(any(
                c.get('unresolved_target_name') == 'Jane Unknown' and c['relationship_type'] == 'parent'
                for c in held
            ))
            self.assertFalse(any('Something Else' in c.get('evidence_line', '') for c in review['relationship_candidates']))

    def test_validator_promotes_only_resolved_approved_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_path, manifest_path, review_path = self._fixture(root)
            review, _, added = MOD.enrich_review(
                vault_root=root,
                review_path=review_path,
                candidate_review_path=candidate_path,
                manifest_path=manifest_path,
            )
            for candidate in added:
                candidate['approved'] = True
            review_path.write_text(json.dumps(review), encoding='utf-8')

            plan, receipt = BASE.validate_reviewed(review_path)
            edges = [p for p in plan['proposals'] if p['proposal_type'] == 'person_relationship_edge']
            self.assertEqual(len(edges), 3)
            self.assertEqual(receipt['approved_relationship_edges'], 3)
            self.assertEqual(receipt['held_or_unresolved_approved_items'], 1)
            self.assertFalse(plan['apply_allowed'])
            serialized = json.dumps(plan)
            self.assertNotIn('Jane Unknown', serialized)
            self.assertNotIn('evidence_line', serialized)
            self.assertNotIn('source_note', serialized)


if __name__ == '__main__':
    unittest.main()
