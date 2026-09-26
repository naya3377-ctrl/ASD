# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
import PySide6
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH)
qt = Path(PySide6.__file__).parent
qml = qt / "qml"
if not qml.exists():
    qml = qt / "Qt" / "qml"
datas = [(str(root / "ui"), "ui"), (str(root / "assets"), "assets"),
         (str(root / "LICENSE"), "."), (str(root / "README.md"), "."),
         (str(root / "THIRD_PARTY_NOTICES.md"), "."),
         (str(qml), str(qml.relative_to(qt.parent)))]
a = Analysis([str(root / "main.py")], pathex=[str(root)], binaries=[], datas=datas,
    hiddenimports=["PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtQuickControls2", "PySide6.QtSvg", "PySide6.QtPrintSupport", "pymupdf"]+collect_submodules("fontTools.ttLib.tables")+collect_submodules("fontTools.cffLib"),
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "PySide6.QtWebEngineCore",
              "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick"],
    noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="YoonDF", debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=False,
    icon=str(root / "assets" / "icon.ico"))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="YoonDF")
