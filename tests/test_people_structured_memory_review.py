import copy
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
SANJAY = '00000000-0000-0000-0000-000000000003'


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
            self.assertGreaterEqual(len(review['date_candidates']), 1)
            birthdays = [c for c in review['date_candidates'] if c['date_type'] == 'birthday']
            self.assertTrue(any(c['person_id'] == ALICE and c['month'] == 4 and c['day'] == 5 for c in birthdays))
            self.assertTrue(all(c['year'] is None for c in birthdays))
            self.assertTrue(any(int(c.get('supporting_evidence_count') or 1) >= 2 for c in birthdays))
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

    def test_sensitive_passing_beats_birthday_word_and_stays_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            people = root / '20 Areas' / 'People'
            sanjay_dir = people / 'Sanjay'
            sanjay_dir.mkdir(parents=True)
            (sanjay_dir / '00 Sanjay.md').write_text(
                '---\naliases: [Sanjay]\ntype: person\n---\n# Sanjay\n', encoding='utf-8'
            )
            (people / 'Recurring.md').write_text(
                "- **[[Sanjay]]** — long-standing friend; Christmas dinners, birthdays. *Sanjay's mom's passing (Jun 13, 2022)* is a yearly anchor.\n",
                encoding='utf-8',
            )
            candidate = {
                'schema_version': 2,
                'entries': [
                    {'source_path': '20 Areas/People/Sanjay/00 Sanjay.md', 'mapping_note_paths': ['20 Areas/People/Sanjay/00 Sanjay.md'], 'note_names': ['Sanjay'], 'existing_person_id': SANJAY},
                ],
            }
            review_path = root / 'candidate.json'
            manifest_path = root / 'manifest.json'
            review_path.write_text(json.dumps(candidate), encoding='utf-8')
            manifest_path.write_text(json.dumps({'links': []}), encoding='utf-8')
            review, receipt = MOD.build_review(
                vault_root=root, candidate_review_path=review_path, manifest_path=manifest_path,
                roots=(Path('20 Areas/People'),),
            )
            self.assertEqual(len(review['date_candidates']), 1)
            memorial = review['date_candidates'][0]
            self.assertEqual(memorial['date_type'], 'memorial')
            self.assertEqual(memorial['sensitivity_class'], 'sensitive')
            self.assertIsNone(memorial['person_id'])
            self.assertEqual(memorial['resolution'], 'unresolved_related_person')
            self.assertEqual((memorial['year'], memorial['month'], memorial['day']), (2022, 6, 13))
            self.assertEqual(receipt['held_unresolved_date_candidates'], 1)
            self.assertFalse(any(c['date_type'] == 'birthday' for c in review['date_candidates']))

    def test_duplicate_recurring_birthday_evidence_collapses_before_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            people = root / '20 Areas' / 'People'
            sanjay_dir = people / 'Sanjay'
            sanjay_dir.mkdir(parents=True)
            (sanjay_dir / '00 Sanjay.md').write_text(
                '---\naliases: [Sanjay]\ntype: person\n---\n# Sanjay\n', encoding='utf-8'
            )
            (people / 'Timeline.md').write_text(
                '- **2018-12-28** — Sanjay birthday\n- **2020-12-28** — Sanjay birthday\n',
                encoding='utf-8',
            )
            candidate = {
                'schema_version': 2,
                'entries': [
                    {'source_path': '20 Areas/People/Sanjay/00 Sanjay.md', 'mapping_note_paths': ['20 Areas/People/Sanjay/00 Sanjay.md'], 'note_names': ['Sanjay'], 'existing_person_id': SANJAY},
                ],
            }
            review_path = root / 'candidate.json'
            manifest_path = root / 'manifest.json'
            review_path.write_text(json.dumps(candidate), encoding='utf-8')
            manifest_path.write_text(json.dumps({'links': []}), encoding='utf-8')
            review, receipt = MOD.build_review(
                vault_root=root, candidate_review_path=review_path, manifest_path=manifest_path,
                roots=(Path('20 Areas/People'),),
            )
            birthdays = [c for c in review['date_candidates'] if c['date_type'] == 'birthday']
            self.assertEqual(len(birthdays), 1)
            self.assertEqual((birthdays[0]['year'], birthdays[0]['month'], birthdays[0]['day']), (None, 12, 28))
            self.assertEqual(birthdays[0]['supporting_evidence_count'], 2)
            self.assertEqual(receipt['collapsed_duplicate_date_evidence'], 1)

    def test_explicit_anniversary_year_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            people = root / '20 Areas' / 'People'
            alice_dir = people / 'Alice Example'
            alice_dir.mkdir(parents=True)
            (alice_dir / '00 Alice.md').write_text(
                '---\naliases: [Alice]\ntype: person\n---\n# Alice\n\nAnniversary Date is March 6 2024\n',
                encoding='utf-8',
            )
            candidate = {
                'schema_version': 2,
                'entries': [
                    {'source_path': '20 Areas/People/Alice Example/00 Alice.md', 'mapping_note_paths': ['20 Areas/People/Alice Example/00 Alice.md'], 'note_names': ['Alice'], 'existing_person_id': ALICE},
                ],
            }
            review_path = root / 'candidate.json'
            manifest_path = root / 'manifest.json'
            review_path.write_text(json.dumps(candidate), encoding='utf-8')
            manifest_path.write_text(json.dumps({'links': []}), encoding='utf-8')
            review, _ = MOD.build_review(
                vault_root=root, candidate_review_path=review_path, manifest_path=manifest_path,
                roots=(Path('20 Areas/People'),),
            )
            anniversary = next(c for c in review['date_candidates'] if c['date_type'] == 'anniversary')
            self.assertEqual((anniversary['year'], anniversary['month'], anniversary['day']), (2024, 3, 6))

    def test_validator_collapses_duplicate_approved_dates(self):
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
            date['approved'] = True
            duplicate = copy.deepcopy(date)
            duplicate['source_sha256'] = 'a' * 64
            review['date_candidates'].append(duplicate)
            reviewed_path = root / 'reviewed.json'
            reviewed_path.write_text(json.dumps(review), encoding='utf-8')
            plan, receipt = MOD.validate_reviewed(reviewed_path)
            dates = [p for p in plan['proposals'] if p['proposal_type'] == 'person_date']
            self.assertEqual(len(dates), 1)
            self.assertEqual(receipt['deduplicated_approved_person_dates'], 1)


if __name__ == '__main__':
    unittest.main()
