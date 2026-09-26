"""Native image extraction and font fidelity regression checks.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import tempfile
import unittest
import fitz
from bichaek.document import Document, DocumentError
from bichaek.fonts import normalized


class MediaFontTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root/'source.pdf'
        self.pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 10), True)
        self.pix.set_rect(self.pix.irect, (40, 80, 120, 160))
        self.png = self.root/'image.png'; self.pix.save(self.png)
        with fitz.open() as pdf:
            page = pdf.new_page(width=600, height=800)
            page.insert_font(fontname='Original', fontbuffer=fitz.Font('tiro').buffer)
            page.insert_text((40, 70), 'ORIGINAL TEXT', fontsize=20, fontname='Original')
            page.insert_image((40, 150, 240, 250), filename=str(self.png))
            page.insert_image((300, 150, 500, 250), filename=str(self.png))
            pdf.save(self.path)
        self.doc = Document(); self.doc.open(str(self.path))

    def tearDown(self): self.doc.close(); self.temp.cleanup()

    def extract(self, item):
        return self.doc.extract_embedded_image(item['page'], item['number'], item['revision'], item['session'], item['pageId'])

    def test_original_font_and_selected_font_reopen(self):
        block = self.doc.objects(0)['blocks'][0]
        self.doc.replace_text(0, block['id'], 'REVISED TEXT', 20, height=50, font_source='original')
        after = self.doc.objects(0)['blocks'][0]
        self.assertEqual(normalized(after['font']), normalized(block['font']))
        selected = self.root/'chosen.otf'; selected.write_bytes(fitz.Font('cobo').buffer)
        self.doc.replace_text(0, after['id'], 'SELECTED FONT', 20, height=50, font_path=str(selected))
        saved = self.root/'saved.pdf'; self.doc.save(str(saved))
        with fitz.open(saved) as reopened:
            self.assertIn('SELECTED FONT', ' '.join(reopened[0].get_text().split()))
            spans = [s for b in reopened[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans']]
            self.assertTrue(any('NimbusMono' in s['font'] and 'Bold' in s['font'] for s in spans), spans)
            self.assertEqual(len(reopened[0].get_image_info()), 2)

    def test_missing_glyph_rolls_back_without_default_font(self):
        block = self.doc.objects(0)['blocks'][0]
        before = self.doc.pdf[0].get_text()
        with self.assertRaises(DocumentError):
            self.doc.replace_text(0, block['id'], '한글 폰트 선택', 20, height=50, font_source='original')
        self.assertEqual(self.doc.pdf[0].get_text(), before)
        self.assertFalse(self.doc.info()['dirty'])

    def test_images_alpha_native_resolution_rotation_and_stale_guard(self):
        items = self.doc.text_layout(0)['images']
        self.assertEqual(len(items), 2)
        self.assertNotIn('png', items[0])
        data = self.extract(items[1]); pix = fitz.Pixmap(data['png'])
        self.assertEqual((pix.width,pix.height,pix.alpha),(20,10,1))
        self.assertEqual(pix.samples,self.pix.samples)
        self.assertFalse(self.doc.info()['dirty'])
        self.doc.rotate([0])
        rotated = self.doc.text_layout(0)['images']
        self.assertEqual(rotated[0]['rect'], list(fitz.Rect(items[0]['rect'])*self.doc.pdf[0].rotation_matrix))
        with self.assertRaises(DocumentError): self.extract(items[0])
        self.assertEqual(self.extract(rotated[0])['png'], data['png'])

    def test_inline_image_and_permissions(self):
        p = self.doc.pdf[0]
        xref = self.doc.pdf.get_new_xref()
        self.doc.pdf.update_object(xref, '<<>>')
        self.doc.pdf.update_stream(xref, b'q 20 0 0 20 50 300 cm BI /W 1 /H 1 /CS /RGB /BPC 8 ID \xff\x00\x00 EI Q')
        self.doc.pdf.xref_set_key(p.xref,'Contents',f'{xref} 0 R')
        self.doc._display_lists.clear()
        item = self.doc.text_layout(0)['images'][0]
        pix = fitz.Pixmap(self.extract(item)['png'])
        self.assertEqual((pix.width,pix.height),(1,1)); self.assertEqual(pix.pixel(0,0),(255,0,0))
        locked = self.root/'locked.pdf'
        self.doc.pdf.save(locked,encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='reader',permissions=0)
        self.doc.open(str(locked),'reader')
        self.assertEqual(self.doc.text_layout(0)['images'],[])
        item = dict(item,session=self.doc.session,revision=self.doc.revision,pageId=self.doc.pdf[0].xref)
        with self.assertRaises(DocumentError): self.extract(item)

    def test_insert_is_saved_and_undoable(self):
        self.doc.add_image(0,[100,350,300,450],str(self.png))
        self.assertEqual(len(self.doc.pdf[0].get_image_info()),3)
        self.doc.undo(); self.assertEqual(len(self.doc.pdf[0].get_image_info()),2)
        self.doc.redo(); self.assertEqual(len(self.doc.pdf[0].get_image_info()),3)
        path=self.root/'inserted.pdf';self.doc.save(str(path))
        with fitz.open(path) as pdf: self.assertEqual(len(pdf[0].get_image_info()),3)

if __name__=='__main__': unittest.main()
