"""Edited text is read back before it is kept.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import unittest
import fitz
from bichaek.document import Document, DocumentError


class WriteVerifyTests(unittest.TestCase):
    def setUp(self):
        self.pdf = fitz.open(); self.page = self.pdf.new_page()
        self.page.insert_text((72, 100), "Edited 문장 text", fontname="korea", fontsize=14)
        self.rect = [60, 80, 400, 110]

    def tearDown(self): self.pdf.close()

    def test_matching_text_passes_ignoring_spaces(self):
        Document._verify_written(self.page, self.rect, list("Edited문장text"))
        Document._verify_written(self.page, self.rect, list("E d i t e d"))

    def test_different_letters_are_refused(self):
        with self.assertRaises(DocumentError):
            Document._verify_written(self.page, self.rect, list("Edited 문자 text"))

    def test_nothing_to_check_is_fine(self):
        Document._verify_written(self.page, self.rect, [" ", "\n"])


if __name__ == "__main__":
    unittest.main()
