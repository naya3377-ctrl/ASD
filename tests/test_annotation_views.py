"""The memo and marked-passage views of the comment list, and the summary.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import tempfile
import unittest
import fitz
from bichaek.annotation_views import split_views, summary_text, threads
from bichaek.document import Document


def item(ident, kind="Highlight", page=0, content="", quote="", depth=0, reply=False, parent="", state=""):
    return {"id": ident, "type": kind, "page": page, "content": content, "quote": quote, "depth": depth,
            "reply": reply, "parentId": parent, "state": state, "label": kind, "color": "#ffd54f"}


class ViewTests(unittest.TestCase):
    def test_plain_marks_leave_the_memo_view(self):
        tree = [item("a", quote="첫 문장"), item("b", "Underline", quote="둘째"), item("c", "StrikeOut", quote="셋째"), item("d", "Squiggly", quote="넷째")]
        notes, marks = split_views(tree)
        self.assertEqual(notes, [])
        self.assertEqual([m["id"] for m in marks], ["a", "b", "c", "d"])
        self.assertTrue(all(m["note"] == "" and m["replies"] == 0 for m in marks))

    def test_a_memo_on_marked_words_is_in_both_views(self):
        tree = [item("a", content="  톤을 맞춰 주세요 ", quote="도입부")]
        notes, marks = split_views(tree)
        self.assertEqual([n["id"] for n in notes], ["a"])
        self.assertEqual(marks[0]["note"], "톤을 맞춰 주세요")

    def test_whitespace_only_memo_counts_as_none(self):
        notes, marks = split_views([item("a", content=" \n\t ", quote="x")])
        self.assertEqual(notes, []); self.assertEqual(len(marks), 1)

    def test_notes_drawings_and_boxes_stay_memos(self):
        tree = [item("n", "Text", content="메모"), item("e", "Text"), item("f", "FreeText", content="상자"),
                item("i", "Ink"), item("s", "Stamp"), item("x", "Square")]
        notes, marks = split_views(tree)
        self.assertEqual([n["id"] for n in notes], ["n", "e", "f", "i", "s", "x"])
        self.assertEqual(marks, [])

    def test_threads_keep_their_replies(self):
        tree = [item("a", quote="표시"), item("r1", "Text", content="답", depth=1, reply=True, parent="a"),
                item("r2", "Text", content="답의 답", depth=2, reply=True, parent="r1"),
                item("b", quote="다른 표시"), item("c", "Text", content="메모")]
        self.assertEqual([[x["id"] for x in g] for g in threads(tree)], [["a", "r1", "r2"], ["b"], ["c"]])
        notes, marks = split_views(tree)
        self.assertEqual([n["id"] for n in notes], ["a", "r1", "r2", "c"])
        self.assertEqual([(m["id"], m["replies"]) for m in marks], [("a", 2), ("b", 0)])
        # Depths are kept in the memo view for indentation, reset in the mark view.
        self.assertEqual([n["depth"] for n in notes], [0, 1, 2, 0])
        self.assertTrue(all(m["depth"] == 0 for m in marks))

    def test_a_reply_whose_parent_is_missing_is_still_a_memo(self):
        tree = [item("r", "Text", content="고아 답글", reply=True, parent="gone")]
        notes, marks = split_views(tree)
        self.assertEqual([n["id"] for n in notes], ["r"]); self.assertEqual(marks, [])

    def test_a_reply_that_is_itself_a_mark_is_not_listed_as_a_passage(self):
        tree = [item("a", "Text", content="메모"), item("m", "Highlight", quote="q", depth=1, reply=True, parent="a")]
        notes, marks = split_views(tree)
        self.assertEqual([n["id"] for n in notes], ["a", "m"]); self.assertEqual(marks, [])

    def test_review_state_keeps_a_mark_in_the_memo_view(self):
        notes, _ = split_views([item("a", quote="q", state="Accepted")])
        self.assertEqual([n["id"] for n in notes], ["a"])

    def test_inputs_are_not_changed(self):
        tree = [item("a", quote="q", depth=3)]
        split_views(tree)
        self.assertEqual(tree[0]["depth"], 3); self.assertNotIn("note", tree[0])

    def test_empty(self):
        self.assertEqual(split_views([]), ([], []))
        self.assertEqual(summary_text([]), "형광펜 모음\n")

    def test_summary_is_page_ordered_plain_text(self):
        marks = split_views([item("a", page=0, quote="첫  줄\n다음 줄", content="확인"), item("b", page=0, quote=""),
                             item("c", page=4, quote="다섯째 쪽")])[1]
        text = summary_text(marks, "도록.pdf")
        self.assertEqual(text, "도록.pdf · 형광펜 모음\n\n1쪽\n· 첫 줄 다음 줄\n  메모: 확인\n· (글자를 읽을 수 없는 표시)\n\n5쪽\n· 다섯째 쪽\n")


class RealPdfViewTests(unittest.TestCase):
    """The views built from what the engine reads back from a saved PDF."""
    def test_marks_and_memos_from_a_real_document(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "views.pdf"
            with fitz.open() as pdf:
                page = pdf.new_page()
                for line in range(4): page.insert_text((72, 100 + line * 30), f"Line number {line + 1} of the catalogue", fontsize=12)
                pdf.save(path)
            doc = Document(); doc.open(str(path))
            try:
                # Character offsets run line after line: each line has 33 characters.
                doc.add_markup(0, "highlight", 0, 10)
                doc.add_markup(0, "underline", 40, 52, content="밑줄 메모")
                doc.add_comment(0, [400, 100], "여백 메모")
                doc.save(str(path))
                doc.open(str(path))
                items = doc.annotations_page(0)["items"]
                tree = [dict(a, depth=0) for a in items]
                notes, marks = split_views(tree)
                self.assertEqual(sorted(n["type"] for n in notes), ["Text", "Underline"])
                self.assertEqual(sorted(m["type"] for m in marks), ["Highlight", "Underline"])
                underline = next(m for m in marks if m["type"] == "Underline")
                self.assertEqual(underline["note"], "밑줄 메모")
                self.assertTrue(all(m["quote"] for m in marks), marks)
                self.assertIn("밑줄 메모", summary_text(marks))
            finally:
                doc.close()


if __name__ == "__main__":
    unittest.main()
