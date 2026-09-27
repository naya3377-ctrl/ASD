"""Icons keep their size on high-DPI (150-200%) Windows displays.

0.9.3-0.9.7 froze when edit mode showed an icon inside a layout: the image's
pixel size fed back into its width and doubled on every layout pass. The check
runs in a child process because the display scale is fixed per QApplication.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

UI = Path(__file__).resolve().parent.parent / 'ui'
CHILD = r'''
import sys, time
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
app = QGuiApplication([])
engine = QQmlApplicationEngine(); engine.load(QUrl.fromLocalFile(sys.argv[1]))
window = engine.rootObjects()[0]
end = time.monotonic() + 1.5
while time.monotonic() < end: app.processEvents()
icon = window.property('probe')
print(window.devicePixelRatio(), icon.property('width'), icon.property('height'))
'''
QML = '''
import QtQuick
import QtQuick.Layouts
import "%s"
Window {
    width: 300; height: 80; visible: true
    property var probe: hint
    RowLayout { anchors.fill: parent; Icon { id: hint; name: "check"; size: 14 } Text { text: "hint"; Layout.fillWidth: true } }
}
'''


class HighDpiIconTests(unittest.TestCase):
    def test_icon_in_layout_keeps_its_size_at_200_percent(self):
        with tempfile.TemporaryDirectory() as folder:
            qml = Path(folder) / 'probe.qml'
            qml.write_text(QML % UI.as_uri(), encoding='utf-8')
            env = dict(os.environ, QT_SCALE_FACTOR='2', QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software')
            done = subprocess.run([sys.executable, '-c', CHILD, str(qml)], env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 0, done.stderr[-2000:])
            ratio, width, height = map(float, done.stdout.split()[-3:])
            self.assertEqual(ratio, 2.0)
            self.assertEqual((width, height), (14.0, 14.0))

    def test_provider_never_builds_a_huge_image(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QGuiApplication
        from bichaek.icons import Icons
        app = QGuiApplication.instance() or QGuiApplication([])
        image = Icons(UI.parent / 'assets' / 'icons').requestImage('check/3c4944', QSize(), QSize(40000, 40000))
        self.assertLessEqual(image.width(), 256)


if __name__ == '__main__':
    unittest.main()
