"""Exercise the actual primary app.run startup and clean shutdown.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    import tempfile
    import time
    import fitz
    from unittest.mock import patch
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication
    from bichaek.tabs import Documents
    from bichaek.app import run

    with tempfile.TemporaryDirectory() as work:
        paths = []
        for i in range(2):
            path = str(Path(work) / f'처음 여는 문서 {i}.pdf')
            with fitz.open() as doc:
                doc.new_page().insert_text((60, 90), 'Startup check')
                doc.save(path)
            paths.append(path)
        original = Documents.__init__
        passed = []

        def observe(self, images):
            original(self, images)
            self.startup_check = QTimer(self)
            deadline = time.monotonic() + 15
            def check():
                if len(self.tabs) == 2 and all(b.document['count'] == 1 for b in self._tabs):
                    assert {b.document['path'] for b in self._tabs} == set(paths)
                    assert len({b.process.pid for b in self._tabs}) == 1
                    assert sum(w.objectName() == 'mainWindow' for w in QGuiApplication.topLevelWindows()) == 1
                    passed.append(True)
                    self.startup_check.stop()
                    QApplication.instance().quit()
                elif time.monotonic() > deadline:
                    self.startup_check.stop()
                    QApplication.instance().exit(1)
            self.startup_check.timeout.connect(check)
            self.startup_check.start(50)

        with patch.dict(os.environ, {'XDG_CACHE_HOME': work, 'LOCALAPPDATA': work}):
            with patch.object(Documents, '__init__', observe), patch.object(sys, 'argv', ['main.py', *paths]):
                assert run() == 0 and passed
        assert not any(Path(work).rglob('owner.json'))
        print('PASS: production primary startup, queued initial arguments, two tabs/one worker, clean relay release')


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
