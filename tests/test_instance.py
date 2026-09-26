"""Real process election, concurrent delivery and crash/exit recovery."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from bichaek.instance import InstanceRelay, pdf_paths


class InstanceTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.root = Path(self.work.name)
        self.folder = self.root / 'launch'
        self.log = self.root / 'events.jsonl'
        self.children = []

    def tearDown(self):
        for child in self.children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
            child.stdout.close()
            child.stderr.close()
        self.work.cleanup()

    def launch(self, *paths):
        helper = Path(__file__).with_name('instance_helper.py')
        p = subprocess.Popen([sys.executable, str(helper), str(self.folder), str(self.log), *paths],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.children.append(p)
        return p

    def events(self):
        if not self.log.exists():
            return []
        # Another process may still be finishing the last JSON line.
        lines = self.log.read_text(encoding='utf-8').splitlines(keepends=True)
        return [json.loads(x) for x in lines if x.endswith('\n')]

    def wait(self, predicate):
        deadline = time.monotonic() + 8
        while not predicate():
            self.assertLess(time.monotonic(), deadline, 'relay did not finish')
            time.sleep(.02)

    def test_simultaneous_first_launch_has_one_reader_and_all_paths(self):
        paths = [str(self.root / ('한글 문서 ' + str(i) + '.pdf')) for i in range(8)]
        for path in paths:
            self.launch(path)
        self.wait(lambda: len(self.events()) == len(paths))
        self.wait(lambda: sum(p.poll() is None for p in self.children) == 1)
        self.assertEqual({p for row in self.events() for p in row['paths']}, set(paths))
        self.assertEqual(len({row['pid'] for row in self.events()}), 1)
        self.assertTrue(all(p.returncode == 0 for p in self.children if p.poll() is not None))
        (self.folder / 'stop').touch()
        for p in self.children:
            p.wait(timeout=5)
        self.assertEqual(sum(p.stdout.read().strip() == 'PRIMARY' for p in self.children), 1)

    def test_crashed_reader_and_stale_owner_do_not_block_restart(self):
        first = self.launch(str(self.root / '첫 파일.pdf'))
        self.wait(lambda: len(self.events()) == 1)
        first.kill()
        first.wait(timeout=5)
        second = self.launch(str(self.root / '다음 파일.pdf'))
        self.wait(lambda: len(self.events()) == 2)
        self.assertNotEqual(self.events()[0]['pid'], self.events()[1]['pid'])
        self.assertIsNone(second.poll())

    def test_closed_reader_releases_lock_with_waiting_launcher(self):
        # Hold the production lock without receiving (as during UI shutdown).
        owner = InstanceRelay(self.folder)
        self.assertTrue(owner.start_or_forward([]))
        try:
            child = self.launch(str(self.root / 'After exit.pdf'))
            self.wait(lambda: len(list(self.folder.glob('r-*.json'))) == 2)
            self.assertIsNone(child.poll())
        finally:
            owner.close()
        self.wait(lambda: any(row['paths'] for row in self.events()))
        self.assertIsNone(child.poll())

    def test_absolute_unicode_arguments_and_invalid_request_rejected(self):
        paths = pdf_paths(['한글 문서.PDF', 'ignore.txt', 'nul\0.pdf'])
        self.assertEqual(paths, [os.path.abspath('한글 문서.PDF')])
        owner = InstanceRelay(self.folder)
        self.assertTrue(owner.start_or_forward([]))
        bad = self.folder / 'r-0-invalid.json'
        owner.write_atomic(bad, {'version': 1, 'paths': ['relative.pdf']})
        received = []
        try:
            owner.poll(lambda p: received.append(p) is None)
            self.assertEqual(received, [[]])
            self.assertIn('error', json.loads(bad.with_suffix('.ack').read_text()))
        finally:
            owner.close()
