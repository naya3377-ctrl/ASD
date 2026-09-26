"""Integration tests assert actual PDF contents after save and reopen.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import multiprocessing as mp
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import fitz
from bichaek.document import Document, DocumentError
from bichaek.worker import ocr_main, ocr_languages
from tests.make_fixture import create


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/"source.pdf"
        create(self.path)
        self.original=self.path.read_bytes()
        self.doc=Document();self.doc.open(str(self.path))

    def tearDown(self):
        self.doc.close();self.temp.cleanup()

    def reopened(self):
        path=Path(self.temp.name)/"saved.pdf"
        self.doc.save(str(path))
        return fitz.open(path)

    def test_real_text_replacement_and_undo(self):
        blocks=self.doc.objects(1)["blocks"]
        block=next(b for b in blocks if b["text"]=="SECOND PAGE")
        self.doc.replace_text(1,block["id"],"REVISED PAGE",24,height=65)
        self.assertNotIn("SECOND PAGE",self.doc.pdf[1].get_text())
        self.assertIn("REVISED PAGE",self.doc.pdf[1].get_text())
        self.doc.undo();self.assertIn("SECOND PAGE",self.doc.pdf[1].get_text())
        self.doc.redo();self.assertNotIn("SECOND PAGE",self.doc.pdf[1].get_text())
        with self.reopened() as out:
            self.assertIn("REVISED PAGE",out[1].get_text())
            self.assertNotIn("SECOND PAGE",out[1].get_text())
            self.assertTrue(out[1].get_drawings())
        self.assertEqual(self.path.read_bytes(),self.original)

    def test_korean_replacement_persists(self):
        block=next(b for b in self.doc.objects(1)["blocks"] if "한글" in b["text"])
        self.doc.replace_text(1,block["id"],"새로운 전시 서문입니다.",18,height=60)
        with self.reopened() as out:
            self.assertIn("새로운 전시 서문입니다.",out[1].get_text())
            self.assertNotIn("한글 본문",out[1].get_text())

    def test_overflow_rolls_back_atomically(self):
        block=self.doc.objects(1)["blocks"][0]
        before=self.doc.pdf[1].get_text()
        with self.assertRaises(DocumentError):
            self.doc.replace_text(1,block["id"],"WAY TOO LONG "*300,80,height=20)
        self.assertEqual(self.doc.pdf[1].get_text(),before)
        self.assertFalse(self.doc.info()["dirty"])

    def test_move_delete_rotate_insert_undo_save(self):
        self.doc.move_page(0,2)
        self.assertIn("SECOND PAGE",self.doc.pdf[0].get_text())
        self.assertIn("A document",self.doc.pdf[2].get_text())
        self.doc.move_page(2,0)
        self.assertIn("A document",self.doc.pdf[0].get_text())
        self.doc.rotate([2],90)
        self.doc.delete_pages([1])
        self.assertEqual(len(self.doc.pdf),3)
        self.doc.undo();self.assertEqual(len(self.doc.pdf),4)
        self.doc.redo();self.assertEqual(len(self.doc.pdf),3)
        self.doc.insert_pdf(str(self.path),1)
        self.assertEqual(len(self.doc.pdf),7)
        self.doc.undo();self.assertEqual(len(self.doc.pdf),3)
        with self.reopened() as out:
            self.assertEqual(len(out),3)
            self.assertEqual(out[1].rotation,90)

    def test_last_page_delete_guard(self):
        with self.assertRaises(DocumentError):self.doc.delete_pages([0,1,2,3])
        self.assertEqual(len(self.doc.pdf),4)

    def test_image_highlight_note_and_text(self):
        image=Path(self.temp.name)/"image.png"
        self.doc.pdf[0].get_pixmap(matrix=fitz.Matrix(.2,.2)).save(image)
        self.doc.add_image(1,[50,660,150,780],str(image))
        self.doc.add_text(1,[200,665,530,735],"New caption",16)
        block=self.doc.objects(1)["blocks"][0]
        self.doc.highlight(1,block["displayRect"])
        self.doc.note(1,[530,100,550,120],"확인할 내용")
        with self.reopened() as out:
            self.assertTrue(out[1].get_images())
            self.assertIn("New caption",out[1].get_text())
            self.assertEqual(len(list(out[1].annots())),2)

    def test_rotation_coordinates(self):
        self.doc.rotate([1],90)
        blocks=self.doc.objects(1)["blocks"]
        b=next(b for b in blocks if b["text"]=="SECOND PAGE")
        self.doc.replace_text(1,b["id"],"ROTATED EDIT",24,height=65)
        self.doc.add_text(1,[100,100,400,180],"Rotated addition",12)
        with self.reopened() as out:
            self.assertEqual(out[1].rotation,90)
            self.assertIn("ROTATED EDIT",out[1].get_text())
            self.assertIn("Rotated addition",out[1].get_text())

    def test_save_to_original_and_dirty_state(self):
        self.doc.rotate([0],90)
        self.doc.save(str(self.path))
        self.assertFalse(self.doc.info()["dirty"])
        self.doc.undo();self.assertTrue(self.doc.info()["dirty"])
        self.doc.redo();self.assertFalse(self.doc.info()["dirty"])
        with fitz.open(self.path) as out:self.assertEqual(out[0].rotation,90)

    def test_failed_save_keeps_original_and_unsaved_document(self):
        self.doc.rotate([0],90)
        with patch('bichaek.document.os.replace',side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):self.doc.save(str(self.path))
        self.assertEqual(self.path.read_bytes(),self.original)
        self.assertEqual(self.doc.pdf[0].rotation,90)
        self.assertTrue(self.doc.info()['dirty'])

    def test_encrypted_pdf(self):
        encrypted=Path(self.temp.name)/'encrypted.pdf'
        self.doc.pdf.save(encrypted,encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='user',
                          permissions=fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY)
        result=self.doc.open(str(encrypted))
        self.assertTrue(result['passwordRequired'])
        result=self.doc.open(str(encrypted),'user')
        self.assertFalse(result['editable'])
        with self.assertRaises(DocumentError):self.doc.rotate([0])
        result=self.doc.open(str(encrypted),'owner')
        self.assertTrue(result['editable'])
        self.doc.rotate([0])
        self.doc.save(str(encrypted))
        with fitz.open(encrypted) as out:
            self.assertTrue(out.needs_pass)
            self.assertTrue(out.authenticate('user'))
            self.assertEqual(out[0].rotation,90)

    def test_region_copy(self):
        b=self.doc.objects(1)['blocks'][0]
        self.assertIn('SECOND PAGE',self.doc.selected_text(1,b['displayRect'])['text'])

    def test_stale_edit_rejected(self):
        revision=self.doc.revision
        self.doc.rotate([0])
        with self.assertRaises(DocumentError):self.doc.replace_text(1,0,"X",12,revision=revision)

    def test_search_and_render(self):
        self.assertTrue(self.doc.search_page(0,"document")["rects"])
        image=self.doc.render(2,800)
        self.assertEqual(image["width"],800)
        self.assertTrue(image["png"].startswith(b"\x89PNG"))

    @unittest.skipUnless("eng" in ocr_languages(),"English Tesseract is not installed")
    def test_ocr_persists_and_preserves_image_pixels(self):
        before=self.doc.pdf[3].get_pixmap().samples
        snapshot=self.doc.ocr_snapshot()
        ctx=mp.get_context("spawn");events=ctx.Queue();cancel=ctx.Event()
        ocr_main(snapshot,[0,3],"eng",self.temp.name,events,cancel)
        done=None
        while done is None:
            msg=events.get(timeout=5)
            if "error" in msg:self.fail(msg["error"])
            if msg.get("done"):done=msg
        self.assertEqual(done["skipped"],1)
        self.doc.merge_ocr(done["results"],done["revision"],done["session"])
        with self.reopened() as out:
            self.assertIn("SCANNED ARCHIVE",out[3].get_text())
            self.assertEqual(before,out[3].get_pixmap().samples)
            self.assertTrue(out[3].search_for("searchable"))

    def test_stale_ocr_rejected(self):
        snap=self.doc.ocr_snapshot()
        self.doc.move_page(0,2)
        with self.assertRaises(DocumentError): self.doc.merge_ocr([],snap["revision"],snap["session"])


if __name__=="__main__":unittest.main()
