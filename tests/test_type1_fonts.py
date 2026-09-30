"""Embedded Type1 subsets (common in Korean InDesign/Illustrator PDFs) are editable.

A Type1 subset holds at most 256 glyphs, so one face is split into several
same-named subsets and one paragraph mixes them. The editor must merge them
into one program instead of failing with "Unknown CFF format".
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile
import unittest
import fitz
from fontTools.misc.psCharStrings import T1CharString
from fontTools.misc import eexec
from bichaek.fonts import original_font, qt_font, type1_to_otf


def charstring(program):
    cs=T1CharString(program=program);cs.compile()
    return eexec.encrypt(b'\0\0\0\0'+cs.bytecode,4330)[0]

def pfa(name,glyphs):
    """glyphs: {code: (glyphname, width, [(x,y),...] square outline)}"""
    enc=' '.join(f'dup {code} /{g[0]} put' for code,g in glyphs.items())
    clear=(f'%!FontType1-1.0: {name}\n12 dict begin\n/FontName /{name} def\n/FontType 1 def\n/PaintType 0 def\n'
           f'/FontMatrix [0.001 0 0 0.001 0 0] readonly def\n/FontBBox {{0 -200 1000 800}} readonly def\n'
           f'/Encoding 256 array 0 1 255 {{1 index exch /.notdef put}} for {enc} readonly def\n'
           'currentdict end\ncurrentfile eexec\n').encode()
    items=[('.notdef',charstring([0,500,'hsbw','endchar']))]
    for code,(g,w,box) in glyphs.items():
        x0,y0,x1,y1=box
        items.append((g,charstring([x0,w,'hsbw',y0,'vmoveto',x1-x0,'hlineto',y1-y0,'vlineto',x0-x1,'hlineto','closepath','endchar'])))
    private=(b'dup /Private 8 dict dup begin\n/RD{string currentfile exch readstring pop}executeonly def\n'
             b'/ND{noaccess def}executeonly def\n/NP{noaccess put}executeonly def\n/MinFeature{16 16}def\n/password 5839 def\n'
             b'/BlueValues [] def\n/Subrs 0 array ND\n2 index /CharStrings '+str(len(items)).encode()+b' dict dup begin\n')
    for g,data in items:private+=f'/{g} {len(data)} RD '.encode()+data+b' ND\n'
    private+=b'end\nend\nreadonly put\nnoaccess put\ndup /FontName get exch definefont pop\nmark currentfile closefile\n'
    body=eexec.encrypt(b'\0\0\0\0'+private,55665)[0].hex().encode()
    body=b'\n'.join(body[i:i+64] for i in range(0,len(body),64))
    return clear+body+b'\n'+(b'0'*64+b'\n')*8+b'cleartomark\n'

def binary_pfa(name,glyphs):
    text=pfa(name,glyphs);head,rest=text.split(b'currentfile eexec\n',1)
    hexpart=rest.split(b'\n'+b'0'*64)[0].replace(b'\n',b'')
    return head+b'currentfile eexec\n',bytes.fromhex(hexpart.decode())

def subset_pdf(path):
    doc=fitz.open();page=doc.new_page(width=300,height=200)
    tounicode=lambda pairs:('/CIDInit /ProcSet findresource begin 12 dict begin begincmap /CMapName /U def 1 begincodespacerange <00> <FF> endcodespacerange '
        f'{len(pairs)} beginbfchar '+' '.join(f'<{c:02X}> <{ord(u):04X}>' for c,u in pairs)+' endbfchar endcmap CMapName currentdict /CMap defineresource pop end end').encode()
    fonts=[]
    for prefix,glyphs,pairs in (('AAAAAA',{1:('cid10',600,(50,0,550,700)),2:('cid11',700,(50,0,650,700))},[(1,'가'),(2,'나')]),
                                ('BAAAAA',{1:('cid12',650,(80,0,560,700))},[(1,'다')])):
        clear,binary=binary_pfa('Test-Regular',glyphs)
        ff=doc.get_new_xref();doc.update_object(ff,'<<>>');doc.update_stream(ff,clear+binary,compress=False)
        doc.xref_set_key(ff,'Length1',str(len(clear)));doc.xref_set_key(ff,'Length2',str(len(binary)));doc.xref_set_key(ff,'Length3','0')
        tu=doc.get_new_xref();doc.update_object(tu,'<<>>');doc.update_stream(tu,tounicode(pairs))
        fd=doc.get_new_xref();doc.update_object(fd,f'<</Type/FontDescriptor/FontName/{prefix}+Test-Regular/Flags 32/FontBBox[0 -200 1000 800]/ItalicAngle 0/Ascent 800/Descent -200/CapHeight 700/StemV 80/FontFile {ff} 0 R>>')
        widths=' '.join(str(glyphs[c][1]) if c in glyphs else '0' for c in range(1,3))
        f=doc.get_new_xref();doc.update_object(f,f'<</Type/Font/Subtype/Type1/BaseFont/{prefix}+Test-Regular/FirstChar 1/LastChar 2/Widths[{widths}]/FontDescriptor {fd} 0 R/ToUnicode {tu} 0 R>>')
        fonts.append(f)
    doc.xref_set_key(page.xref,'Resources',f'<</Font<</F1 {fonts[0]} 0 R/F2 {fonts[1]} 0 R>>>>')
    c=doc.get_new_xref();doc.update_object(c,'<<>>');doc.update_stream(c,b'BT /F1 30 Tf 20 120 Td <0102> Tj /F2 30 Tf <01> Tj ET')
    doc.xref_set_key(page.xref,'Contents',f'{c} 0 R');doc.save(path)



class Type1SubsetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'type1.pdf'
        subset_pdf(self.path);self.doc=fitz.open(self.path)
    def tearDown(self):
        self.doc.close();self.tmp.cleanup()

    def test_same_named_subsets_merge_with_original_advances(self):
        self.assertEqual(self.doc[0].get_text().strip(),'가나다')
        data=original_font(self.doc,0,'Test-Regular','가나다')
        font=fitz.Font(fontbuffer=data)
        self.assertEqual(sorted(map(chr,font.valid_codepoints())),['가','나','다'])
        self.assertAlmostEqual(font.text_length('가나다',fontsize=1000),600+700+650,places=2)
        family=qt_font(data)[1];self.assertTrue(family.startswith('YoonDF_'))

    def test_missing_trailer_and_pfb_are_accepted(self):
        xref=self.doc[0].get_fonts()[0][0];raw=self.doc.extract_font(xref)[3]
        self.assertNotIn(b'cleartomark',raw)          # Length3 0, as many producers write it
        self.assertTrue(type1_to_otf(self.doc,[(xref,raw)]))

    def test_live_editor_opens_type1_paragraph(self):
        from PySide6.QtWidgets import QApplication
        from bichaek.document import Document
        from bichaek.text_editor import TextEditor
        from tests.test_inline_fonts import EditorBridge
        app=QApplication.instance() or QApplication([])
        d=Document();d.open(str(self.path));editor=TextEditor(EditorBridge(d))
        try:
            target=d.objects(0)['blocks'][0]
            target.update(pageWidth=300,pageHeight=200,session=d.session,revision=d.revision)
            editor.start(target);editor.loadFonts()
            self.assertTrue(editor.ready,editor.status);self.assertFalse(editor._invalid())
        finally:
            editor.dispose();d.close()

    def test_edited_paragraph_stays_real_text_and_can_be_edited_again(self):
        """Regression: after one edit the paragraph became uneditable on Windows."""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QTextCursor
        from bichaek.document import Document
        from bichaek.text_editor import TextEditor
        from tests.test_inline_fonts import EditorBridge
        app=QApplication.instance() or QApplication([])
        d=Document();d.open(str(self.path))
        try:
            for round_text in ('나','가다'):
                editor=TextEditor(EditorBridge(d))
                try:
                    target=d.objects(0)['blocks'][0]
                    target.update(pageWidth=300,pageHeight=200,session=d.session,revision=d.revision)
                    editor.start(target);editor.loadFonts();self.assertTrue(editor.ready,editor.status)
                    cursor=QTextCursor(editor.doc);cursor.movePosition(QTextCursor.End);cursor.insertText(round_text)
                    self.assertTrue(editor.canApply,editor.status);editor.apply()
                finally:
                    editor.dispose()
                blocks=d.objects(0)['blocks']
                self.assertEqual(len(blocks),1)
                self.assertFalse(blocks[0]['hidden'])
                self.assertTrue(blocks[0]['text'].replace('\n','').endswith(round_text),blocks[0]['text'])
            self.assertEqual(d.pdf[0].get_text().replace('\n',''),'가나다나가다')
            # Written as text in the original face, not outlines or a substitute.
            self.assertTrue(all(t['type']==0 for t in d.pdf[0].get_texttrace()))
            self.assertTrue(any('Test-Regular' in f[3] for f in d.pdf[0].get_fonts()))
        finally:
            d.close()


if __name__=='__main__':
    unittest.main()
