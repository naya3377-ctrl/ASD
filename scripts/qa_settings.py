"""Real QML settings layout and mocked OS handoff; no Windows execution claim.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    import fitz
    from types import SimpleNamespace
    from unittest.mock import patch
    from PySide6.QtCore import QObject, QUrl, Qt, QByteArray, qInstallMessageHandler
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from bichaek.bridge import Images
    from bichaek.tabs import Documents

    root = Path(__file__).resolve().parent.parent
    QQuickStyle.setStyle(os.environ.get('YOONDF_QA_STYLE','Basic'))
    app = QApplication([])
    QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font("korea").buffer))
    warnings = []
    qInstallMessageHandler(lambda kind, context, text: warnings.append(text)
                           if 'file:' in text or 'Error' in text else None)
    images = Images()
    documents = Documents(images)
    bridge = documents.activeBridge
    errors = []
    documents.showError.connect(errors.append)
    engine = QQmlApplicationEngine()
    engine.addImageProvider('pages', images)
    engine.rootContext().setContextProperty('bridge', bridge)
    engine.rootContext().setContextProperty('documents', documents)
    engine.load(QUrl.fromLocalFile(str(root / 'ui/Main.qml')))
    assert engine.rootObjects(), warnings
    window = engine.rootObjects()[0]
    window.setProperty("uiFontFamily", "Droid Sans Fallback")

    def item(name):
        value = window.findChild(QObject, name)
        assert value is not None, name
        return value

    def click(name):
        obj = item(name)
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier,
                         obj.mapToScene(obj.boundingRect().center()).toPoint())
        QTest.qWait(100)

    try:
        # Expose the Windows-only section to test its real layout on Linux.
        item('defaultAppsSection').setProperty('visible', True)
        for w, h in [(1000, 640), (1320, 900)]:
            window.resize(w, h)
            QTest.qWait(100)
            click('settingsButton')
            dialog = item('settingsDialog')
            assert dialog.property('visible')
            assert dialog.property('y') >= 0, (dialog.property('y'), dialog.property('height'), window.height(), window.contentItem().height(), warnings)
            assert dialog.property('height') <= window.height()
            assert item('defaultAppsButton').width() > 100
            scroll = item('settingsScroll')
            assert scroll.property('contentWidth') <= scroll.property('availableWidth') + 1
            if h == 640:
                (root / 'test-output').mkdir(exist_ok=True)
                window.grabWindow().save(str(root / 'test-output/settings-061.png'))
            # Actual click must close our modal and hand off to Windows settings.
            with patch('bichaek.bridge.os', SimpleNamespace(name='nt')):
                with patch('PySide6.QtGui.QDesktopServices.openUrl', return_value=True) as opened:
                    click('defaultAppsButton')
                    assert not dialog.property('visible')
                    opened.assert_called_once()
                    assert opened.call_args.args[0].toString() == 'ms-settings:defaultapps'
        print('PASS: settings fit 1000x640 and 1320x900; real QML button closes modal and opens the supported settings URI')

        with patch('bichaek.bridge.os', SimpleNamespace(name='nt')):
            with patch('PySide6.QtGui.QDesktopServices.openUrl', return_value=False):
                bridge.openDefaultAppsSettings()
        assert len(errors) == 1 and '.pdf' in errors[0] and '기본 앱' in errors[0]
        with patch('bichaek.bridge.os', SimpleNamespace(name='posix')):
            with patch('PySide6.QtGui.QDesktopServices.openUrl') as opened:
                bridge.openDefaultAppsSettings()
                opened.assert_not_called()
        assert len(errors) == 2 and 'Windows' in errors[1]
        assert not warnings, warnings
        print('PASS: failed OS handoff has manual instructions; non-Windows guard; no QML warnings')
    finally:
        window.setVisible(False)
        documents.shutdown()
        del engine
        qInstallMessageHandler(None)


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
