"""Comments on PDFs with damaged or unusual structure.

A damaged object that no page uses made every comment fail with
"code=8: invalid key in dict": the undo copy could not be written.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import struct
import tempfile
import unittest
import fitz
from bichaek.document import Document
from bichaek.worker import describe

fitz.TOOLS.mupdf_display_errors(False)
CONTENT = b"BT /F1 24 Tf 72 700 Td (Alpha beta gamma delta) Tj ET"


def objects(page_extra=b""):
    return {1: b"<< /Type /Catalog /Pages 2 0 R >>",
            2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R " + page_extra + b">>",
            4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            5: b"<< /Length %d >>\nstream\n" % len(CONTENT) + CONTENT + b"\nendstream"}


def write_pdf(path, body, trailer=b"", compressed=None):
    """A hand-written PDF. `compressed` puts {num: object} in an object stream
    listed by an xref stream, as newer exporters do."""
    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    body = dict(body)
    if compressed:
        header, data = b"", b""
        for num, obj in compressed.items():
            header += b"%d %d " % (num, len(data)); data += obj + b" "
        stream = header + data
        body[max(body) + 1] = b"<< /Type /ObjStm /N %d /First %d /Length %d >>\nstream\n" % (len(compressed), len(header), len(stream)) + stream + b"\nendstream"
    for num in sorted(body):
        offsets[num] = len(out)
        out += b"%d 0 obj\n" % num + body[num] + b"\nendobj\n"
    if not compressed:
        size = max(body) + 1; start = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % size
        for num in range(1, size):
            out += b"%010d 00000 n \n" % offsets[num] if num in offsets else b"0000000000 65535 f \n"
        out += b"trailer\n<< /Size %d /Root 1 0 R %s>>\nstartxref\n%d\n%%%%EOF\n" % (size, trailer, start)
    else:
        holder = max(body); xref = max(max(body), max(compressed)) + 1; start = len(out)
        rows = b""
        for num in range(xref + 1):
            if num == 0: rows += struct.pack(">BIH", 0, 0, 65535)
            elif num in compressed: rows += struct.pack(">BIH", 2, holder, list(compressed).index(num))
            elif num == xref: rows += struct.pack(">BIH", 1, start, 0)
            elif num in offsets: rows += struct.pack(">BIH", 1, offsets[num], 0)
            else: rows += struct.pack(">BIH", 0, 0, 0)
        out += (b"%d 0 obj\n<< /Type /XRef /Size %d /W [1 4 2] /Root 1 0 R %s/Length %d >>\nstream\n" % (xref, xref + 1, trailer, len(rows))
                + rows + b"\nendstream\nendobj\nstartxref\n%d\n%%%%EOF\n" % start)
    Path(path).write_bytes(bytes(out))


class DamagedStructureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)

    def tearDown(self): self.tmp.cleanup()

    def comment_everything(self, path, password=""):
        doc = Document(); doc.open(str(path), password)
        try:
            self.assertTrue(doc.text_layout(0)["chars"])
            doc.add_comment(0, [50, 60], "안녕 (괄호) \\ 백슬래시", author="사용자")
            doc.add_markup(0, "highlight", 0, 5, author="사용자", content="제목 확인")
            items = doc.annotations_page(0)["items"]
            mine = [x for x in items if x["name"].startswith("bichaek-")]
            self.assertEqual({x["type"] for x in mine}, {"Text", "Highlight"})
            note = next(x for x in mine if x["type"] == "Text")
            doc.update_annotation(0, note["id"], "수정", "검토자", "#7dbbe6", revision=doc.revision)
            doc.reply_annotation(0, note["id"], "답글", "답글러", revision=doc.revision)
            doc.move_annotation(0, note["id"], [200, 220], doc.session, doc.revision)
            doc.undo(); doc.redo()
            out = self.root / (Path(path).stem + "-saved.pdf")
            doc.save(str(out))
        finally:
            doc.close()
        with fitz.open(out) as check:
            if check.needs_pass: check.authenticate(password)
            found = {a.info["content"] for a in check[0].annots()}
            self.assertLessEqual({"수정", "답글", "제목 확인"}, found)
            self.assertEqual(check[0].get_text().split()[:2], ["Alpha", "beta"])

    def test_damaged_object_nothing_uses(self):
        body = objects(); body[6] = b"<< /Type /StructElem /S /P /Alt (x) 3 >>"
        write_pdf(self.root / "unused.pdf", body)
        self.comment_everything(self.root / "unused.pdf")

    def test_damaged_document_info(self):
        body = objects(); body[6] = b"<< /Title (x) /Producer 12 (Hancom) >>"
        write_pdf(self.root / "info.pdf", body, trailer=b"/Info 6 0 R ")
        self.comment_everything(self.root / "info.pdf")

    def test_damaged_member_of_object_stream(self):
        write_pdf(self.root / "objstm.pdf", objects(),
                  compressed={6: b"<< /Good 1 >>", 7: b"<< /Bad 1 (x) 2 >>", 8: b"[1 2 3]"})
        self.comment_everything(self.root / "objstm.pdf")

    def test_damaged_comment_among_good_ones(self):
        body = objects(b"/Annots [6 0 R 7 0 R] ")
        body[6] = b"<< /Type /Annot /Subtype /Text /Rect [100 100 120 120] /Contents (good) /NM (good) >>"
        body[7] = b"<< /Type /Annot /Subtype /Text /Rect [200 100 220 120] 5 /Contents (bad) >>"
        write_pdf(self.root / "annots.pdf", body)
        doc = Document(); doc.open(str(self.root / "annots.pdf"))
        try:
            layout = doc.text_layout(0)
            self.assertTrue(layout["chars"])
            self.assertIn("good", [x["content"] for x in layout["annotations"]])
        finally:
            doc.close()
        self.comment_everything(self.root / "annots.pdf")

    def test_unreadable_stream_length(self):
        body = objects(); body[5] = b"<< /Length 99 0 R >>\nstream\n" + CONTENT + b"\nendstream"
        write_pdf(self.root / "length.pdf", body)
        self.comment_everything(self.root / "length.pdf")

    def test_mupdf_errors_are_explained(self):
        body = objects(); body[6] = b"<< /A 1 (x) 2 >>"
        write_pdf(self.root / "raw.pdf", body)
        with fitz.open(self.root / "raw.pdf") as pdf, self.assertRaises(Exception) as caught:
            pdf.save(self.root / "copy.pdf")   # MuPDF alone, without the repair
        message = describe(caught.exception)
        self.assertIn("PDF 내부 구조", message)
        self.assertIn("invalid key in dict", message)
        self.assertEqual(describe(ValueError("메모 내용을 입력해 주세요.")), "메모 내용을 입력해 주세요.")


class PermissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.path = Path(self.tmp.name) / "restricted.pdf"

    def tearDown(self): self.tmp.cleanup()

    def restricted(self, permissions):
        with fitz.open() as pdf:
            page = pdf.new_page(); page.insert_text((72, 100), "Secret words here", fontsize=18)
            pdf.save(self.path, encryption=fitz.PDF_ENCRYPT_AES_128, owner_pw="owner", user_pw="", permissions=permissions)
        doc = Document(); doc.open(str(self.path)); self.addCleanup(doc.close)
        return doc

    def test_comments_allowed_copying_not(self):
        doc = self.restricted(fitz.PDF_PERM_PRINT | fitz.PDF_PERM_ANNOTATE)
        layout = doc.text_layout(0)
        self.assertFalse(layout["copyable"]); self.assertTrue(layout["markable"])
        # Positions to mark, no characters to copy.
        self.assertEqual({c[0] for c in layout["chars"]} - {" "}, {"•"})
        doc.add_markup(0, "underline", 0, 6, content="확인")
        item = doc.annotations_page(0)["items"][0]
        self.assertEqual((item["type"], item["content"], item["quote"]), ("Underline", "확인", ""))

    def test_comments_not_allowed(self):
        doc = self.restricted(fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY)
        self.assertTrue(doc.text_layout(0)["copyable"])
        for action in (lambda: doc.add_comment(0, [50, 50], "x"), lambda: doc.add_markup(0, "highlight", 0, 3)):
            with self.assertRaisesRegex(Exception, "주석 권한"):
                action()


if __name__ == "__main__":
    unittest.main()
