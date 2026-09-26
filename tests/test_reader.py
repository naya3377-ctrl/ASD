"""PDF permissions and geometry regressions for reading and printing.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import tempfile
from pathlib import Path
import unittest
import fitz
from bichaek.document import Document, DocumentError


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'source.pdf'
        pdf=fitz.open();pdf.new_page(width=600,height=800);pdf.new_page()
        p=pdf[0];p.insert_text((40,70),'Text selection',fontsize=20)
        p.insert_link({'kind':fitz.LINK_URI,'from':fitz.Rect(40,50,200,80),'uri':'https://example.com'})
        p.insert_link({'kind':fitz.LINK_GOTO,'from':fitz.Rect(40,100,200,130),'page':1,'to':fitz.Point(20,40)})
        pdf.save(self.path);pdf.close()
        self.doc=Document();self.doc.open(str(self.path))
    def tearDown(self):self.doc.close();self.temp.cleanup()
    def test_characters_and_rotation_link_geometry(self):
        initial=self.doc.text_layout(0)
        self.assertEqual(''.join(c[0] for c in initial['chars']),'Text selection')
        self.doc.rotate([0])
        rotated=self.doc.text_layout(0)
        for old,new in zip(initial['chars'],rotated['chars']):
            expected=fitz.Rect(old[1:5])*self.doc.pdf[0].rotation_matrix
            for a,b in zip(expected,new[1:5]):self.assertAlmostEqual(a,b,places=3)
        links=rotated['links']
        expected=fitz.Rect(initial['links'][0]['rect'])*self.doc.pdf[0].rotation_matrix
        self.assertEqual(list(expected),links[0]['rect'])
        self.assertEqual(links[1]['page'],1)
    def test_permissions_preserve_links_block_copy_and_print(self):
        restricted=Path(self.temp.name)/'restricted.pdf'
        self.doc.pdf.save(restricted,encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='reader',permissions=0)
        state=self.doc.open(str(restricted),'reader')
        self.assertFalse(state['printable'])
        data=self.doc.text_layout(0)
        self.assertFalse(data['copyable']);self.assertEqual(data['chars'],[])
        self.assertEqual(data['links'][0]['uri'],'https://example.com')
        with self.assertRaises(DocumentError):self.doc.render_print(0)
        state=self.doc.open(str(restricted),'owner')
        self.assertTrue(state['printable']);self.assertTrue(self.doc.text_layout(0)['chars'])
    def test_low_quality_print_limit(self):
        restricted=Path(self.temp.name)/'print-low.pdf'
        self.doc.pdf.save(restricted,encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='reader',permissions=fitz.PDF_PERM_PRINT)
        state=self.doc.open(str(restricted),'reader')
        self.assertTrue(state['printable']);self.assertFalse(state['printHighQuality'])
        result=self.doc.render_print(0,300)
        self.assertLessEqual(result['width'],1251)
    def test_internal_destination_after_page_reorder(self):
        self.doc.move_page(1,0)
        links=self.doc.text_layout(1)['links']
        self.assertEqual(next(x for x in links if x['kind']=='page')['page'],0)

if __name__=='__main__':unittest.main()
