"""Bundled UI typography; PDF text keeps its own font pipeline.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
from pathlib import Path
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtQuick import QQuickWindow

FAMILY = "Pretendard"
WEIGHTS = ("Regular", "Medium", "SemiBold", "Bold")

def configure_ui_fonts(app, root: Path):
    """Register unmodified OFL static outlines before creating any QML window.

    Scalable Qt distance-field rendering avoids native bitmap resampling and
    LCD colour fringes on fractional-DPI Windows displays. Qt 6 handles
    device pixel ratio; font sizes stay in logical pixels, never scaled twice.
    Static weights avoid variable-font differences between Windows renderers.
    """
    loaded = 0
    for weight in WEIGHTS:
        path = root / "assets" / "fonts" / FAMILY / f"{FAMILY}-{weight}.ttf"
        if QFontDatabase.addApplicationFont(str(path)) >= 0: loaded += 1
        else:
            # A damaged or blocked font file must never stop the app from
            # opening: note it and let the system UI font stand in.
            from .diagnostics import note
            note("UI font could not be loaded: %s", path.name)
    family = FAMILY if loaded else ("Malgun Gothic" if os.name == "nt" else "Noto Sans CJK KR")
    font = QFont(family)
    font.setPixelSize(15)
    font.setHintingPreference(QFont.PreferNoHinting)
    font.setStyleStrategy(QFont.PreferAntialias | QFont.NoSubpixelAntialias)
    app.setFont(font)
    QQuickWindow.setTextRenderType(QQuickWindow.QtTextRendering)
    return font
