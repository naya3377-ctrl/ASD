"""Bundled typefaces (SIL OFL 1.1, see assets/fonts).

YoonDF Display (from Playfair Display) sets headlines, YoonDF Text (from
Source Serif 4) sets text, JetBrains Mono sets numbers and labels, and Nanum
Myeongjo sets Korean. The Latin faces have no Hangul; each of them falls back
to Nanum Myeongjo, so Korean in any role stays in the same serif voice.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path

DISPLAY = "YoonDF Display"
TEXT = "YoonDF Text"
MONO = "JetBrains Mono"
KOREAN = "NanumMyeongjo"


def install(folder):
    """Register every font in `folder`; returns the family names loaded."""
    from PySide6.QtGui import QFont, QFontDatabase
    loaded = set()
    for path in sorted(Path(folder).glob("*.ttf")):
        index = QFontDatabase.addApplicationFont(str(path))
        if index >= 0:
            loaded.update(QFontDatabase.applicationFontFamilies(index))
    if KOREAN in loaded:
        for family in (DISPLAY, TEXT, MONO):
            QFont.insertSubstitution(family, KOREAN)
    return loaded
