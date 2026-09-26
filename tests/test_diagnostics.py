"""GUI freezes are written to the local log with the GUI thread's stack.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import logging
import time
import unittest


class StallWatchTests(unittest.TestCase):
    def test_freeze_is_logged_with_location_and_length(self):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        from bichaek.diagnostics import StallWatch
        app=QApplication.instance() or QApplication([])
        logger=logging.getLogger('yoondf');records=[]
        handler=logging.Handler();handler.emit=records.append;logger.addHandler(handler);logger.setLevel(logging.INFO)
        watch=StallWatch(limit=.4)
        def blocking_work(): time.sleep(.9)
        try:
            QTimer.singleShot(100,blocking_work)
            deadline=time.monotonic()+4
            while time.monotonic()<deadline and not any('ended' in r.getMessage() for r in records):
                app.processEvents();time.sleep(.02)
        finally:
            watch.stop();logger.removeHandler(handler)
        messages=[r.getMessage() for r in records]
        self.assertTrue(any('blocking_work' in m for m in messages),messages)
        self.assertTrue(any('freeze ended' in m for m in messages),messages)


class OlderReaderTests(unittest.TestCase):
    """After an update, a still-open older window must not silently receive files."""
    def test_older_or_unstamped_owner_is_reported_same_version_is_forwarded(self):
        import json, tempfile
        from pathlib import Path
        from bichaek import __version__
        from bichaek.instance import InstanceRelay, OlderReaderRunning
        with tempfile.TemporaryDirectory() as folder:
            owner=InstanceRelay(folder)
            try:
                self.assertTrue(owner.start_or_forward([]))
                stamp=json.loads((Path(folder)/'owner.json').read_text(encoding='utf-8'))
                self.assertEqual(stamp['appVersion'],__version__)
                for old in ({'pid':1},{'pid':1,'appVersion':'0.0.1'}):
                    (Path(folder)/'owner.json').write_text(json.dumps(old),encoding='utf-8')
                    late=InstanceRelay(folder)
                    try:
                        with self.assertRaises(OlderReaderRunning) as caught:late.start_or_forward([],timeout=.3)
                        self.assertIn('닫은 뒤 다시 실행',str(caught.exception))
                    finally:late.close()
                (Path(folder)/'owner.json').write_text(json.dumps(stamp),encoding='utf-8')
                late=InstanceRelay(folder)
                try:
                    with self.assertRaises(RuntimeError) as caught:late.start_or_forward([],timeout=.3)
                    self.assertNotIsInstance(caught.exception,OlderReaderRunning)   # forwarded, owner just did not poll
                finally:late.close()
            finally:
                owner.close()


if __name__=='__main__':
    unittest.main()
