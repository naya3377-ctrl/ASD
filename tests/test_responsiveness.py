"""Edits redraw only changed pages; font preparation is reused; reader history.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch
import fitz
from bichaek.document import Document
from tests.make_fixture import create


class PageTokenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "source.pdf"
        create(self.path)
        self.doc = Document(); self.state = self.doc.open(str(self.path))

    def tearDown(self):
        self.doc.close(); self.temp.cleanup()

    def texts(self):
        return [p.get_text().split("\n")[0] for p in self.doc.pdf]

    def test_text_edit_changes_only_that_page(self):
        before = self.state["pageTokens"]
        block = next(b for b in self.doc.objects(1)["blocks"] if b["text"] == "SECOND PAGE")
        after = self.doc.replace_text(1, block["id"], "REVISED", 24, height=65)["pageTokens"]
        self.assertEqual([a == b for a, b in zip(before, after)], [True, False, True, True])
        self.assertEqual(self.doc.undo()["pageTokens"], before)
        self.assertEqual(self.doc.redo()["pageTokens"], after)

    def test_tokens_follow_reordered_deleted_and_inserted_pages(self):
        pairs = dict(zip(self.state["pageTokens"], self.texts()))
        for step in (lambda: self.doc.move_pages([0], 3), lambda: self.doc.move_page(2, 0),
                     lambda: self.doc.move_pages([1, 3], 0), lambda: self.doc.delete_pages([1])):
            tokens = step()["pageTokens"]
            self.assertEqual([pairs[t] for t in tokens], self.texts())
        tokens = self.doc.insert_pdf(str(self.path), 1)["pageTokens"]
        self.assertEqual(len(tokens), len(self.doc.pdf))
        self.assertEqual(len(set(tokens)), len(tokens))
        self.assertEqual(tokens[0], self.doc.undo()["pageTokens"][0])

    def test_annotation_and_rotation_tokens(self):
        before = self.state["pageTokens"]
        after = self.doc.add_comment(2, [40, 40], "memo")
        self.assertEqual(self.doc.info()["pageTokens"][:2], before[:2])
        self.assertNotEqual(self.doc.info()["pageTokens"][2], before[2])
        rotated = self.doc.rotate([0])["pageTokens"]
        self.assertNotEqual(rotated[0], before[0]); self.assertEqual(rotated[1], before[1])

    def test_failed_edit_restores_tokens(self):
        before = self.state["pageTokens"]
        with self.assertRaises(Exception):
            with self.doc.transaction(pages=[0]):
                self.doc.pdf[0].insert_text((50, 50), "x")
                raise RuntimeError("boom")
        self.assertEqual(self.doc.page_tokens, before)

    def test_outline(self):
        pdf = fitz.open(self.path)
        pdf.set_toc([[1, "처음", 1], [2, "  둘째\n절 ", 2, {"kind": fitz.LINK_GOTO, "page": 1, "to": fitz.Point(0, 400)}]])
        target = Path(self.temp.name) / "toc.pdf"; pdf.save(target); pdf.close()
        self.doc.open(str(target))
        items = self.doc.outline()["items"]
        self.assertEqual([(i["level"], i["title"], i["page"]) for i in items], [(1, "처음", 0), (2, "둘째 절", 1)])
        self.assertAlmostEqual(items[1]["y"], 400, delta=1)


class FontCacheTests(unittest.TestCase):
    def test_prepared_fonts_are_reused_and_known_gaps_skip_the_job(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "s.pdf"; create(path)
        doc = Document(); doc.open(str(path)); self.addCleanup(doc.close)
        data = fitz.Font("helv").buffer
        calls = []
        def job(payload):
            calls.append(dict(payload["requests"]))
            return {"fonts": [{"name": n, "data": data, "family": "F", "error": "", "partial": "가" in t}
                              for n, t in payload["requests"].items()]}
        with patch("bichaek.font_jobs.run_job", side_effect=job):
            doc.editor_fonts(0, {"Helv": "abc"})
            doc.editor_fonts(0, {"Helv": "cab ba"})
            self.assertEqual(len(calls), 1)
            self.assertTrue(doc.editor_fonts(0, {"Helv": "ab가"})["fonts"][0]["partial"])
            self.assertEqual(len(calls), 2)
            # Typing more of a character already known to be missing: no new job.
            again = doc.editor_fonts(0, {"Helv": "a가b가"})["fonts"][0]
            self.assertTrue(again["partial"]); self.assertFalse(again["error"])
            self.assertEqual(len(calls), 2)
            doc.editor_fonts(0, {"Helv": "a나"})   # a new missing character asks once
            self.assertEqual(len(calls), 3)
            doc.add_comment(0, [30, 30], "memo")   # page content changed → fresh
            doc.editor_fonts(0, {"Helv": "abc"})
            self.assertEqual(len(calls), 4)


class InstalledFontCacheTests(unittest.TestCase):
    def test_catalog_survives_process_restart(self):
        from bichaek import fonts
        with tempfile.TemporaryDirectory() as cache, patch.dict(os.environ, {"XDG_CACHE_HOME": cache, "LOCALAPPDATA": cache}):
            fonts.installed_fonts.cache_clear()
            first = fonts.installed_fonts()
            fonts.installed_fonts.cache_clear()
            with patch.object(fonts, "_scan", side_effect=AssertionError("rescanned")):
                self.assertEqual(fonts.installed_fonts(), first)
            fonts.installed_fonts.cache_clear()


class LibraryTests(unittest.TestCase):
    def setUp(self):
        from PySide6.QtCore import QCoreApplication, QSettings
        self.app = QCoreApplication.instance() or QCoreApplication([])
        self.temp = tempfile.TemporaryDirectory()
        self.settings = QSettings(str(Path(self.temp.name) / "s.ini"), QSettings.IniFormat)

    def tearDown(self):
        self.temp.cleanup()

    def test_recent_and_resume(self):
        from bichaek.library import Library
        a = Path(self.temp.name) / "a.pdf"; a.write_bytes(b"%PDF")
        lib = Library(self.settings)
        self.assertEqual(lib.opened(str(a), "a.pdf", 10), 0)
        lib.remember(str(a), 7); lib.flush()
        again = Library(self.settings)
        self.assertEqual(again.recent[0]["page"], 7)
        self.assertEqual(again.opened(str(a), "a.pdf", 10), 7)
        self.assertEqual(again.opened(str(a), "a.pdf", 5), 0)   # file shrank
        again.forget(str(a)); self.assertEqual(again.recent, [])
        again.setEnabled(False)
        self.assertEqual(again.opened(str(a), "a.pdf", 10), 0); self.assertEqual(again.recent, [])


class TabOrderTests(unittest.TestCase):
    def test_dragging_tabs_keeps_the_active_document(self):
        from PySide6.QtWidgets import QApplication
        from bichaek.rendering import Images
        from bichaek.tabs import Documents
        app = QApplication.instance() or QApplication([])
        docs = Documents(Images())
        try:
            docs.newTab(); docs.newTab()
            ids = [t["id"] for t in docs.tabs]
            docs.activate(0)
            docs.moveTab(0, 2)
            self.assertEqual([t["id"] for t in docs.tabs], [ids[1], ids[2], ids[0]])
            self.assertEqual(docs.activeIndex, 2); self.assertEqual(docs.activeBridge.document_id, ids[0])
            docs.moveTab(1, 0)
            self.assertEqual([t["id"] for t in docs.tabs], [ids[2], ids[1], ids[0]])
            self.assertEqual(docs.activeBridge.document_id, ids[0])
            docs.moveTab(0, 5)   # out of range is ignored
            self.assertEqual(docs.tabModel.rowCount(), 3)
        finally:
            docs.shutdown()


if __name__ == "__main__":
    unittest.main()
