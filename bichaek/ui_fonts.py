"""Bundled UI typography; PDF text keeps its own font pipeline.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
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
    for weight in WEIGHTS:
        path = root / "assets" / "fonts" / FAMILY / f"{FAMILY}-{weight}.ttf"
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            raise RuntimeError(f"UI font could not be loaded: {path.name}")
    font = QFont(FAMILY)
    font.setPixelSize(15)
    font.setHintingPreference(QFont.PreferNoHinting)
    font.setStyleStrategy(QFont.PreferAntialias | QFont.NoSubpixelAntialias)
    app.setFont(font)
    QQuickWindow.setTextRenderType(QQuickWindow.QtTextRendering)
    return font
