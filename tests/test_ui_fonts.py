"""The bundled UI font loads, and a missing font never stops startup.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile
import unittest
from PySide6.QtWidgets import QApplication
from bichaek.ui_fonts import configure_ui_fonts

ROOT=Path(__file__).resolve().parent.parent


class UiFontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_bundled_font(self):
        self.assertEqual(configure_ui_fonts(self.app,ROOT).family(),'Pretendard')

    def test_missing_font_falls_back(self):
        with tempfile.TemporaryDirectory() as empty:
            font=configure_ui_fonts(self.app,Path(empty))
        self.assertTrue(font.family())
        self.assertEqual(font.pixelSize(),15)

if __name__=='__main__':unittest.main()
