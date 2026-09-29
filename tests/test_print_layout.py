"""Print preview and printer share one page placement.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import unittest
from bichaek.printing import parse_range, place, needs_rotation, paper_orientation


class PrintLayoutTests(unittest.TestCase):
    def test_page_ranges(self):
        self.assertEqual(parse_range("1-3, 5", 10), [0, 1, 2, 4])
        self.assertEqual(parse_range("8-", 10), [7, 8, 9])
        self.assertEqual(parse_range("-2 7", 10), [0, 1, 6])
        self.assertEqual(parse_range("3-1", 10), [2, 1, 0])
        self.assertEqual(parse_range("4~5", 10), [3, 4])
        for bad in ["", "0", "11", "a-3", "-", "2-12"]:
            with self.assertRaises(ValueError): parse_range(bad, 10)

    def test_fit_actual_and_shrink(self):
        area = (0, 0, 500, 800)
        self.assertEqual(place(250, 400, area, "fit"), (0, 0, 500, 800))
        self.assertEqual(place(250, 400, area, "actual"), (125, 200, 250, 400))
        self.assertEqual(place(250, 400, area, "shrink"), (125, 200, 250, 400))   # small pages stay 100 %
        x, y, w, h = place(1000, 1600, area, "shrink")                           # large ones shrink
        self.assertEqual((round(w), round(h)), (500, 800))

    def test_auto_rotation_follows_paper(self):
        self.assertTrue(needs_rotation(842, 595, 595, 842, True))     # landscape page, portrait paper
        self.assertFalse(needs_rotation(842, 595, 595, 842, False))   # orientation chosen by hand
        self.assertFalse(needs_rotation(595, 842, 595, 842, True))
        self.assertFalse(needs_rotation(600, 600, 595, 842, True))    # square pages never turn
        x, y, w, h = place(842, 595, (0, 0, 595, 842), "fit", rotate=True)
        self.assertAlmostEqual(w, 595); self.assertAlmostEqual(h, 842)

    def test_paper_orientation_by_majority(self):
        self.assertEqual(paper_orientation([(842, 595), (842, 595), (595, 842)]), "landscape")
        self.assertEqual(paper_orientation([(595, 842), (842, 595)]), "portrait")


if __name__ == "__main__":
    unittest.main()
