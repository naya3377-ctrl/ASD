"""Where the main window opens.

Left to itself the window manager may drop the window at a screen corner or
half across two monitors (reported with dual monitors on Windows). Open it
where it was last closed when that spot is still on a connected monitor;
otherwise centred on the monitor the user is working on (the one under the
pointer), never larger than that monitor's usable area.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from PySide6.QtCore import QRect
from PySide6.QtGui import QCursor, QGuiApplication, QWindow


def fitted_rect(area, width, height, minimum_width=0, minimum_height=0, margin=.92):
    """A rectangle of the preferred size, shrunk to fit `area`, centred in it."""
    w = min(width, int(area.width() * margin))
    h = min(height, int(area.height() * margin))
    w = min(max(w, minimum_width), area.width())
    h = min(max(h, minimum_height), area.height())
    return QRect(area.x() + (area.width() - w) // 2, area.y() + (area.height() - h) // 2, w, h)


def saved_rect(value, areas):
    """The remembered rectangle if it still sits (almost) wholly on one monitor."""
    try:
        x, y, w, h = (int(v) for v in value)
    except (TypeError, ValueError):
        return None
    rect = QRect(x, y, w, h)
    if w < 200 or h < 150:
        return None
    for area in areas:
        overlap = area.intersected(rect)
        if overlap.width() * overlap.height() >= .9 * w * h:
            return rect
    return None


def place_window(window, preferences=None):
    screens = QGuiApplication.screens()
    remembered = saved_rect(preferences.value("windowRect") if preferences else None,
                            [s.availableGeometry() for s in screens])
    if remembered is not None:
        screen = QGuiApplication.screenAt(remembered.center()) or QGuiApplication.primaryScreen()
        window.setScreen(screen)
        window.setGeometry(remembered)
        if preferences.value("windowMaximized", False) in (True, "true"):
            window.setVisibility(QWindow.Maximized)
        return
    screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
    if screen is None:
        return
    window.setScreen(screen)
    window.setGeometry(fitted_rect(screen.availableGeometry(), window.width(), window.height(),
                                   window.minimumWidth(), window.minimumHeight()))


def remember_window(window, preferences):
    """Store the normal (not maximized) rectangle and whether it was maximized."""
    maximized = window.visibility() == QWindow.Maximized
    if window.visibility() in (QWindow.Windowed, QWindow.Maximized):
        preferences.setValue("windowMaximized", maximized)
        if not maximized:
            g = window.geometry()
            preferences.setValue("windowRect", [g.x(), g.y(), g.width(), g.height()])
