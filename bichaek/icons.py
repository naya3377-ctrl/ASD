"""Tinted toolbar icons so one SVG set works in light and dark themes.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import re
from threading import RLock

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer

INK = "#38474b"


class Icons(QQuickImageProvider):
    """image://icon/<name>/<rrggbb> renders assets/icons/<name>.svg in a colour."""

    def __init__(self, folder):
        super().__init__(QQuickImageProvider.Image)
        self.folder = Path(folder)
        self.sources = {}
        self.lock = RLock()

    def svg(self, name):
        with self.lock:
            if name not in self.sources:
                path = self.folder / (name + ".svg")
                self.sources[name] = path.read_text(encoding="utf-8") if path.is_file() else ""
            return self.sources[name]

    def requestImage(self, identifier, size, requestedSize):
        name, _, colour = identifier.partition("/")
        colour = colour.split("?", 1)[0]
        if not re.fullmatch(r"[0-9a-fA-F]{6}", colour or ""):
            colour = INK[1:]
        edge = max(requestedSize.width(), requestedSize.height(), 0) or 48
        image = QImage(edge, edge, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        source = self.svg(re.sub(r"[^a-z0-9-]", "", name.lower()))
        if source:
            renderer = QSvgRenderer(QByteArray(source.replace(INK, "#" + colour).encode("utf-8")))
            painter = QPainter(image)
            painter.setRenderHint(QPainter.Antialiasing)
            renderer.render(painter)
            painter.end()
        if size is not None:
            try:
                size.setWidth(edge); size.setHeight(edge)
            except AttributeError:
                pass
        return image
