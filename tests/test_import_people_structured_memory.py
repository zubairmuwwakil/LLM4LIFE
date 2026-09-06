import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'


def load_module():
    sys.path.insert(0, str(SCRIPTS))
    name = 'import_people_structured_memory_test'
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / 'import_people_structured_memory.py')
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MOD = load_module()
ALICE = '00000000-0000-0000-0000-000000000001'
BOB = '00000000-0000-0000-0000-000000000002'
SHA = 'a' * 64


def base_plan():
    return {
        'schema_version': 1,
        'private_artifact': True,
        'apply_allowed': False,
        'proposals': [
            {
                'proposal_type': 'person_date', 'person_id': ALICE, 'date_type': 'birthday',
                'label': None, 'year': None, 'month': 4, 'day': 5, 'recurrence': 'annual',
                'source_kind': 'user_edited_import', 'source_system_id': 'obsidian',
                'confidence': 1.0, 'sensitivity_class': 'standard', 'source_sha256': SHA,
            },
            {
                'proposal_type': 'person_relationship_edge', 'source_person_id': ALICE,
                'target_person_id': BOB, 'relationship_type': 'sibling', 'status': 'active',
                'started_on': None, 'ended_on': None, 'source_kind': 'user_edited_import',
                'source_system_id': 'obsidian', 'confidence': 1.0,
                'sensitivity_class': 'standard', 'source_sha256': SHA,
            },
        ],
        'policy': {
            'requires_separate_apply_authorization': True,
            'raw_evidence_in_plan': False,
            'unresolved_relationship_edges_allowed': False,
            'sensitive_auto_persist_allowed': False,
        },
    }


class StructuredMemoryImporterTests(unittest.TestCase):
    def test_normalization_is_deterministic(self):
        dates1, edges1 = MOD.normalize_plan(base_plan())
        dates2, edges2 = MOD.normalize_plan(base_plan())
        self.assertEqual(dates1[0].id, dates2[0].id)
        self.assertEqual(edges1[0].id, edges2[0].id)

    def test_sensitive_proposal_is_refused(self):
        plan = base_plan()
        plan['proposals'][0]['sensitivity_class'] = 'sensitive'
        with self.assertRaisesRegex(ValueError, 'refuses sensitive'):
            MOD.normalize_plan(plan)

    def test_self_edge_is_refused(self):
        plan = base_plan()
        plan['proposals'][1]['target_person_id'] = ALICE
        with self.assertRaisesRegex(ValueError, 'self-edge'):
            MOD.normalize_plan(plan)

    def test_invalid_date_is_refused(self):
        plan = base_plan()
        plan['proposals'][0]['month'] = 2
        plan['proposals'][0]['day'] = 31
        with self.assertRaises(ValueError):
            MOD.normalize_plan(plan)

    def test_policy_gate_is_required(self):
        plan = base_plan()
        plan['policy']['requires_separate_apply_authorization'] = False
        with self.assertRaisesRegex(ValueError, 'separate apply authorization'):
            MOD.normalize_plan(plan)

    def test_normalized_ops_do_not_contain_note_paths_or_raw_evidence(self):
        dates, edges = MOD.normalize_plan(base_plan())
        serialized = json.dumps({'dates': [d.__dict__ for d in dates], 'edges': [e.__dict__ for e in edges]}, default=str)
        self.assertNotIn('source_note', serialized)
        self.assertNotIn('evidence_line', serialized)


if __name__ == '__main__':
    unittest.main()
