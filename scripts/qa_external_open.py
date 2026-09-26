"""Real subprocess launches into one QML reader, including protected dialogs.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
from pathlib import Path
import sys
import tempfile
import subprocess
import time
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    import fitz
    from PySide6.QtCore import QUrl, QObject, Qt, QTimer, QByteArray, qInstallMessageHandler
    from PySide6.QtGui import QFontDatabase, QWindow
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication, QDialog
    from PySide6.QtTest import QTest
    from bichaek.instance import InstanceRelay
    from bichaek.external_open import ExternalOpenQueue
    from bichaek.bridge import Images
    from bichaek.tabs import Documents

    root = Path(__file__).resolve().parent.parent
    work = tempfile.TemporaryDirectory()
    folder = Path(work.name)
    # The real main.py subprocesses discover the same isolated user cache.
    old_env = {key: os.environ.get(key) for key in ['XDG_CACHE_HOME', 'LOCALAPPDATA']}
    os.environ['XDG_CACHE_HOME'] = str(folder)
    os.environ['LOCALAPPDATA'] = str(folder)
    paths = []
    for i in range(12):
        path = folder / f'한글 자료 {i + 1}.pdf'
        with fitz.open() as doc:
            for j in range(3):
                page = doc.new_page()
                page.insert_text((60, 90), f'DOCUMENT {i + 1} / PAGE {j + 1}', fontsize=22)
            doc.save(path)
        paths.append(str(path))

    relay = InstanceRelay()
    assert relay.start_or_forward([paths[0]])
    QQuickStyle.setStyle('Basic')
    app = QApplication([])
    QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font('korea').buffer))
    warnings = []
    qInstallMessageHandler(lambda kind, context, text: warnings.append(text)
                           if 'file:' in text or 'ReferenceError' in text or 'TypeError' in text else None)
    images = Images()
    documents = Documents(images)
    first = documents.activeBridge
    auto = first.automaticOcr
    first.setAutomaticOcr(False)
    errors = []
    documents.showError.connect(errors.append)
    external = ExternalOpenQueue(documents)
    engine = QQmlApplicationEngine()
    engine.addImageProvider('pages', images)
    engine.rootContext().setContextProperty('bridge', first)
    engine.rootContext().setContextProperty('documents', documents)
    engine.rootContext().setContextProperty('externalRequests', external)
    engine.load(QUrl.fromLocalFile(str(root / 'ui/Main.qml')))
    assert engine.rootObjects(), warnings
    window = engine.rootObjects()[0]
    window.setProperty('uiFontFamily', 'Droid Sans Fallback')
    external.attach(window)
    timer = QTimer()
    timer.timeout.connect(lambda: relay.poll(external.receive))
    timer.start(50)
    children = []

    def wait(predicate, timeout=20):
        start = time.monotonic()
        while not predicate():
            app.processEvents()
            QTest.qWait(15)
            assert time.monotonic() - start < timeout, (errors, warnings, documents.tabs)
        app.processEvents()
        QTest.qWait(80)

    def settled():
        return not window.property('switching') and not window.property('restoring')

    def launch(*files):
        child = subprocess.Popen([sys.executable, str(root / 'main.py'), *files], cwd=str(folder),
                                 env=os.environ.copy(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        children.append(child)
        return child

    def sent(child):
        wait(lambda: child.poll() is not None)
        assert child.returncode == 0, child.communicate()

    def opened(count, active):
        wait(lambda: len(documents.tabs) == count and settled() and not external.pending and
             all(b.document['count'] == 3 and not b.busy for b in documents._tabs) and
             documents.activeBridge.document.get('path') == active)

    def item(name):
        value = window.findChild(QObject, name)
        assert value is not None, name
        return value

    try:
        opened(1, paths[0])
        worker = documents.hub.process.pid
        first.edit('add_text', {'page': 0, 'rect': [60, 130, 480, 170], 'text': 'KEEP UNSAVED EDITS', 'size': 16})
        wait(lambda: not first.busy and first.document['dirty'])
        sent(launch(paths[1]))
        opened(2, paths[1])
        sent(launch(paths[0]))
        opened(2, paths[0])
        assert first.document['dirty']
        print('PASS: actual main.py second launch opens a tab; Unicode/spaced paths; duplicate selects original unsaved tab', flush=True)

        window.showMinimized()
        sent(launch(paths[1]))
        opened(2, paths[1])
        assert window.visibility() == QWindow.Windowed
        window.showMaximized()
        QTest.qWait(80)
        window.showMinimized()
        sent(launch())
        assert window.visibility() == QWindow.Maximized and len(documents.tabs) == 2
        window.showNormal()
        print('PASS: minimized reader restores normal/maximized state; shortcut with no PDF reuses the reader', flush=True)

        documents.activate(0)
        wait(settled)
        first.composeComment(0, 70, 220)
        wait(lambda: item('annotationEditor').property('visible'))
        item('commentBody').setProperty('text', '작성 중인 주석 초안')
        sent(launch(paths[2]))
        assert len(documents.tabs) == 2 and documents.activeBridge is first and external.pending
        assert item('commentBody').property('text') == '작성 중인 주석 초안'
        assert not window.close() and window.isVisible()
        wait(lambda: item('draftCloseDialog').property('visible'))
        button = item('continueEditing')
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier,
                         button.mapToScene(button.boundingRect().center()).toPoint())
        wait(lambda: not item('draftCloseDialog').property('visible'))
        assert item('commentBody').property('text') == '작성 중인 주석 초안'
        QTest.keyClick(window, Qt.Key_Escape)
        opened(3, paths[2])
        assert first.document['dirty']
        dialog = QDialog()
        dialog.setModal(True)
        dialog.show()
        QTest.qWait(80)
        sent(launch(paths[3]))
        assert len(documents.tabs) == 3 and external.pending
        dialog.close()
        opened(4, paths[3])
        print('PASS: QML comment drafts and native modal dialogs defer external files; queued requests prevent accidental reader close', flush=True)

        QTest.keyClick(window, Qt.Key_F5)
        wait(lambda: window.property('presenting'))
        sent(launch(paths[4]))
        opened(5, paths[4])
        assert not window.property('presenting')
        burst = [launch(paths[i]) for i in range(5, 10)]
        for child in burst:
            sent(child)
        wait(lambda: len(documents.tabs) == 10 and not external.pending and
             all(b.document['count'] == 3 and not b.busy for b in documents._tabs) and settled())
        assert documents.hub.process.pid == worker
        assert len({b.process.pid for b in documents._tabs}) == 1
        assert len(documents.hub.frames.frames) == 2
        assert sum(w.objectName() == 'mainWindow' for w in app.topLevelWindows()) == 1
        assert first.document['dirty']
        print('PASS: external file exits slideshow; five concurrent real launches yield ten tabs, one reader and one PDF worker', flush=True)

        documents._closing = True
        documents.closingChanged.emit()
        last = launch(paths[10], paths[11])
        QTest.qWait(300)
        assert last.poll() is None and len(documents.tabs) == 10
        documents._cancel_close()
        sent(last)
        opened(12, paths[11])
        assert not errors, errors
        assert not warnings, warnings
        print('PASS: closing gate retries without losing a multi-file request; no QML warnings', flush=True)
    finally:
        timer.stop()
        external.timer.stop()
        relay.stop()
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
            child.stdout.close()
            child.stderr.close()
        first.setAutomaticOcr(auto)
        window.setVisible(False)
        documents.shutdown()
        del engine
        relay.close()
        qInstallMessageHandler(None)
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        work.cleanup()


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
