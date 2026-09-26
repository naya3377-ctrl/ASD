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


if __name__=='__main__':
    unittest.main()
