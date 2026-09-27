"""Renaming the open PDF from its tab: on disk, without closing, keeping edits.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import tempfile
import unittest
import fitz
from bichaek.document import Document, DocumentError


class RenameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.path = self.root / "원본.pdf"
        with fitz.open() as pdf:
            for i in range(3):
                pdf.new_page().insert_text((60, 80), f"PAGE {i+1}")
            pdf.save(self.path)
        self.doc = Document(); self.doc.open(str(self.path))

    def tearDown(self):
        self.doc.close(); self.temp.cleanup()

    def test_clean_rename_moves_file_and_keeps_document_open(self):
        session, revision = self.doc.session, self.doc.revision
        info = self.doc.rename_file("새 이름")
        self.assertEqual(info["name"], "새 이름.pdf")
        self.assertFalse(self.path.exists())
        self.assertTrue((self.root / "새 이름.pdf").exists())
        # Nothing about the content changed: handles and rendered pages stay valid.
        self.assertEqual((self.doc.session, self.doc.revision), (session, revision))
        self.assertIn("PAGE 2", self.doc.pdf[1].get_text())
        self.assertFalse(info["dirty"])

    def test_unsaved_edits_survive_and_save_goes_to_new_name(self):
        self.doc.delete_pages([2])
        self.assertTrue(self.doc.info()["dirty"])
        info = self.doc.rename_file("편집본.pdf")
        self.assertTrue(info["dirty"]); self.assertEqual(info["count"], 2)
        with fitz.open(self.root / "편집본.pdf") as disk:
            self.assertEqual(len(disk), 3)          # the file on disk is untouched
        self.doc.undo(); self.assertEqual(len(self.doc.pdf), 3)
        self.doc.redo(); self.doc.save(self.doc.path)
        with fitz.open(self.root / "편집본.pdf") as disk:
            self.assertEqual(len(disk), 2)
        self.assertFalse(self.path.exists())

    def test_refuses_existing_name_and_bad_characters(self):
        (self.root / "다른 파일.pdf").write_bytes(self.path.read_bytes())
        with self.assertRaises(DocumentError): self.doc.rename_file("다른 파일")
        for bad in ["a/b", "a:b", "  ", "CON", "what?"]:
            with self.assertRaises(DocumentError): self.doc.rename_file(bad)
        self.assertTrue(self.path.exists())
        self.assertIn("PAGE 1", self.doc.pdf[0].get_text())

    def test_same_name_is_a_no_op(self):
        info = self.doc.rename_file("원본")
        self.assertEqual(info["path"], str(self.path.resolve()))


if __name__ == "__main__":
    unittest.main()
