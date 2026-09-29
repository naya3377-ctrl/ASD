"""Where the main window opens.

Left to itself the window manager may drop the window at a screen corner or
half across two monitors (reported with dual monitors on Windows). Open it
centred on the monitor the user is working on (the one under the pointer),
never larger than that monitor's usable area.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from PySide6.QtCore import QRect
from PySide6.QtGui import QCursor, QGuiApplication


def fitted_rect(area, width, height, minimum_width=0, minimum_height=0, margin=.92):
    """A rectangle of the preferred size, shrunk to fit `area`, centred in it."""
    w = min(width, int(area.width() * margin))
    h = min(height, int(area.height() * margin))
    w = min(max(w, minimum_width), area.width())
    h = min(max(h, minimum_height), area.height())
    return QRect(area.x() + (area.width() - w) // 2, area.y() + (area.height() - h) // 2, w, h)


def place_window(window):
    screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
    if screen is None:
        return
    window.setScreen(screen)
    window.setGeometry(fitted_rect(screen.availableGeometry(), window.width(), window.height(),
                                   window.minimumWidth(), window.minimumHeight()))
