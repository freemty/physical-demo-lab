import copy
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'check_closeout', Path(__file__).resolve().parents[1]/'scripts/check_closeout.py')
closeout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(closeout)


class CloseoutTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ('report.md', 'lesson.md', 'evidence.json', 'demo.py'):
            (self.root/name).write_text('verified fixture\n')
        self.demo = {
            'id': 'demo001', 'title': 'Fixture', 'status': 'complete',
            'scope': 'scripted baseline', 'verified_at': '2026-09-06',
            'limitations': ['No visual perception'],
            'report': 'report.md', 'lessons': ['lesson.md'],
            'evidence': ['evidence.json'],
            'implementation': {'demo.py': hashlib.sha256((self.root/'demo.py').read_bytes()).hexdigest()},
        }

    def check_demo(self, demo=None, required=None):
        return closeout.validate(self.root, {'schema_version': 1, 'demos': [demo or self.demo]}, required)

    def test_complete(self):
        self.assertEqual([], self.check_demo(required='demo001'))

    def test_no_lessons_is_not_complete(self):
        self.demo['lessons'] = []
        self.assertTrue(self.check_demo())

    def test_missing_report(self):
        (self.root/'report.md').unlink()
        self.assertTrue(self.check_demo())

    def test_stale_implementation(self):
        (self.root/'demo.py').write_text('changed implementation\n')
        self.assertTrue(self.check_demo())

    def test_planned_is_not_completion(self):
        self.demo = {'id': 'demo001', 'title': 'Fixture', 'status': 'planned'}
        self.assertEqual([], self.check_demo())
        self.assertTrue(self.check_demo(required='demo001'))

    def test_duplicate_ids(self):
        ledger = {'schema_version': 1, 'demos': [self.demo, copy.deepcopy(self.demo)]}
        self.assertTrue(closeout.validate(self.root, ledger))

    def test_unknown_demo(self):
        self.assertTrue(self.check_demo(required='demo999'))

    def test_path_escape(self):
        self.demo['report'] = '../report.md'
        self.assertTrue(self.check_demo())

    def test_invalid_status_and_empty_limits(self):
        self.demo['limitations'] = []
        self.assertTrue(self.check_demo())
        self.demo['status'] = 'almost_done'
        self.assertTrue(self.check_demo())


if __name__ == '__main__':
    unittest.main()
