"""The Windows title bar follows the app theme.

Windows draws the title bar itself, so by default it stays light (or the
Windows accent colour) even when the app is dark. DWM window attributes set
dark mode (Windows 10 1809+) and, on Windows 11, the caption and title text
colours, so the title bar joins the tab strip below it as one surface.
Elsewhere this does nothing.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QColor

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19   # Windows 10 before 20H1
DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36


def colorref(color):
    """QColor → Windows COLORREF (0x00BBGGRR)."""
    color = QColor(color)
    return color.red() | (color.green() << 8) | (color.blue() << 16)


class WindowFrame(QObject):
    def __init__(self, window=None):
        super().__init__()
        self.window = window
        self.applied = None

    @Slot(bool, QColor, QColor)
    def apply(self, dark, caption, text):
        self.applied = (bool(dark), QColor(caption).name(), QColor(text).name())
        if os.name != "nt" or self.window is None:
            return
        try:
            import ctypes
            from ctypes import wintypes
            hwnd = wintypes.HWND(int(self.window.winId()))
            dwm = ctypes.windll.dwmapi
            def set_attr(attribute, value):
                data = ctypes.c_int(value)
                return dwm.DwmSetWindowAttribute(hwnd, wintypes.DWORD(attribute), ctypes.byref(data), ctypes.sizeof(data))
            if set_attr(DWMWA_USE_IMMERSIVE_DARK_MODE, int(bool(dark))) != 0:
                set_attr(DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, int(bool(dark)))
            # Windows 11 only; older systems return an error and keep their colours.
            set_attr(DWMWA_CAPTION_COLOR, colorref(caption))
            set_attr(DWMWA_TEXT_COLOR, colorref(text))
            set_attr(DWMWA_BORDER_COLOR, colorref(caption))
        except Exception:
            pass
