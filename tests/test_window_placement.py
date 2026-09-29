"""The main window opens centred on one monitor and never larger than it.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import unittest
from PySide6.QtCore import QRect
from bichaek.window_placement import fitted_rect, saved_rect


class WindowPlacementTests(unittest.TestCase):
    def test_centres_on_the_given_monitor(self):
        # Right-hand monitor of a dual setup, left of it at x = -1920.
        area = QRect(-1920, 0, 1920, 1040)
        rect = fitted_rect(area, 1320, 900, 1000, 640)
        self.assertTrue(area.contains(rect))
        self.assertEqual((rect.width(), rect.height()), (1320, 900))
        self.assertEqual(rect.center().x() // 10, area.center().x() // 10)

    def test_shrinks_to_a_small_monitor(self):
        area = QRect(1920, 40, 1280, 680)
        rect = fitted_rect(area, 1320, 900, 1000, 640)
        self.assertTrue(area.contains(rect))
        self.assertLessEqual(rect.height(), 680)
        self.assertGreaterEqual(rect.width(), 1000)

    def test_minimum_never_exceeds_the_monitor(self):
        area = QRect(0, 0, 900, 600)
        rect = fitted_rect(area, 1320, 900, 1000, 640)
        self.assertTrue(area.contains(rect))

    def test_remembered_spot_only_while_its_monitor_is_there(self):
        left, right = QRect(-1920, 0, 1920, 1040), QRect(0, 0, 2560, 1400)
        self.assertEqual(saved_rect([-1800, 50, 1200, 800], [left, right]), QRect(-1800, 50, 1200, 800))
        # The left monitor was unplugged: do not open off screen.
        self.assertIsNone(saved_rect([-1800, 50, 1200, 800], [right]))
        # Straddling two monitors is not "on one monitor".
        self.assertIsNone(saved_rect([-600, 50, 1200, 800], [left, right]))
        self.assertIsNone(saved_rect(None, [right]))
        self.assertIsNone(saved_rect(["x", 1, 2, 3], [right]))


if __name__ == "__main__":
    unittest.main()
