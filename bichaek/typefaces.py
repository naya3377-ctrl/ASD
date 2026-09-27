"""Bundled typeface: Pretendard (SIL OFL 1.1, see assets/fonts).

One family for the whole interface, in the manner of the macOS system font:
Latin, figures and Hangul are drawn together, so every line keeps one voice.
Hanja fall back to the system fonts.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path

TEXT = "Pretendard"


def install(folder):
    """Register every font in `folder`; returns the family names loaded."""
    from PySide6.QtGui import QFontDatabase
    loaded = set()
    for path in sorted(Path(folder).glob("*.otf")) + sorted(Path(folder).glob("*.ttf")):
        index = QFontDatabase.addApplicationFont(str(path))
        if index >= 0:
            loaded.update(QFontDatabase.applicationFontFamilies(index))
    return loaded
