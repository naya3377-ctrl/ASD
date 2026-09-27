"""SPDX-License-Identifier: AGPL-3.0-or-later"""
from pathlib import Path
import os
import sys


def run():
    from .diagnostics import install
    install()
    from .instance import InstanceRelay, pdf_paths
    relay = None
    try:
        relay = InstanceRelay()
        if not relay.start_or_forward(pdf_paths(sys.argv[1:])):
            return 0
        return run_primary(relay)
    except (OSError, RuntimeError, ValueError) as exc:
        from PySide6.QtWidgets import QApplication, QMessageBox
        from .instance import OlderReaderRunning
        app = QApplication.instance() or QApplication(sys.argv)
        if isinstance(exc, OlderReaderRunning):
            QMessageBox.information(None, '윤DF 업데이트', str(exc))
        else:
            QMessageBox.warning(None, '윤DF · 파일 열기', str(exc))
        return 1
    finally:
        if relay:
            relay.close()


def run_primary(relay):
    from PySide6.QtCore import QUrl, QTimer, QSettings
    from PySide6.QtGui import QFont, QIcon
    from PySide6.QtWidgets import QApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from .bridge import Images
    from .tabs import Documents
    from .external_open import ExternalOpenQueue
    from .library import Library
    from .icons import Icons

    preferences=QSettings("Bichaek","BichaekPDF")
    if preferences.value("graphicsMode","auto")=="software":
        os.environ["QT_QUICK_BACKEND"]="software"
    elif os.name=="nt":
        os.environ.setdefault("QSG_RHI_BACKEND","d3d11")
    if os.name=='nt':
        import ctypes
        identify=ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
        identify.argtypes=[ctypes.c_wchar_p];identify.restype=ctypes.c_long
        identify('YoonDF.Reader')
    QQuickStyle.setStyle("Basic")
    app = QApplication(sys.argv)
    app.setApplicationName("YoonDF")
    app.setApplicationDisplayName("윤DF")
    app.setOrganizationName("Bichaek")
    from . import __version__
    app.setApplicationVersion(__version__)
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    from .typefaces import install, TEXT
    loaded = install(root / "assets" / "fonts")
    # Interface text only: Pretendard (bundled), then the Windows system faces.
    # PDF text keeps its own fonts.
    font = QFont()
    font.setFamilies(([TEXT] if TEXT in loaded else []) + ["Segoe UI Variable Text", "Segoe UI", "Malgun Gothic", "Noto Sans CJK KR"])
    font.setPointSize(10)
    app.setFont(font)
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addFile(str(root / "assets" / "icon" / f"{size}.png"))
    app.setWindowIcon(icon)
    images = Images()
    library = Library(preferences)
    documents = Documents(images)
    documents.library = library
    external = ExternalOpenQueue(documents)
    engine = QQmlApplicationEngine()
    engine.addImageProvider("pages", images)
    engine.addImageProvider("icon", Icons(root / "assets" / "icons"))
    engine.rootContext().setContextProperty("bridge", documents.activeBridge)
    engine.rootContext().setContextProperty("documents", documents)
    engine.rootContext().setContextProperty("externalRequests", external)
    engine.rootContext().setContextProperty("library", library)
    engine.rootContext().setContextProperty("iconTint", True)
    engine.load(QUrl.fromLocalFile(str(root / "ui" / "Main.qml")))
    if not engine.rootObjects():
        documents.shutdown()
        return 1
    external.attach(engine.rootObjects()[0])
    launch_timer = QTimer()
    launch_timer.setInterval(100)
    launch_timer.timeout.connect(lambda: relay.poll(external.receive))
    launch_timer.start()
    QTimer.singleShot(0, lambda: relay.poll(external.receive))
    app.aboutToQuit.connect(launch_timer.stop)
    app.aboutToQuit.connect(external.timer.stop)
    app.aboutToQuit.connect(relay.stop)
    app.aboutToQuit.connect(library.flush)
    app.aboutToQuit.connect(documents.shutdown)
    from .diagnostics import StallWatch, note
    note("YoonDF %s started: Qt %s, graphics %s, screen scale %.2f", app.applicationVersion(),
         __import__("PySide6").__version__, os.environ.get("QT_QUICK_BACKEND") or os.environ.get("QSG_RHI_BACKEND", "default"),
         app.primaryScreen().devicePixelRatio() if app.primaryScreen() else 1.0)
    watch = StallWatch()
    app.aboutToQuit.connect(watch.stop)
    result = app.exec()
    # Explicitly destroy the QML engine while its context is still alive.
    del engine
    return result
