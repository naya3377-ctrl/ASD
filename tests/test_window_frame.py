"""The Windows title bar is given the theme's colours in COLORREF form.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import unittest
from PySide6.QtGui import QColor
from bichaek.window_frame import colorref, WindowFrame


class WindowFrameTests(unittest.TestCase):
    def test_colorref_is_bgr(self):
        self.assertEqual(colorref(QColor("#f5f5f7")), 0xF7F5F5)
        self.assertEqual(colorref("#2a2a2c"), 0x2C2A2A)

    def test_apply_without_a_window_is_harmless(self):
        frame = WindowFrame()
        frame.apply(True, QColor("#2a2a2c"), QColor("#f5f5f7"))
        self.assertEqual(frame.applied, (True, "#2a2a2c", "#f5f5f7"))


if __name__ == "__main__":
    unittest.main()
