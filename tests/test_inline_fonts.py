"""Subset-font recovery, exact live layout export, mixed styles and TTC faces."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from io import BytesIO
import tempfile,unittest,re
import fitz
from fontTools.ttLib import TTFont,TTCollection
from PySide6.QtCore import QObject,Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication
from bichaek.document import Document
from bichaek.fonts import original_font,qt_font,normalized,font_bytes,names_of
from bichaek.text_editor import TextEditor


class EditorBridge(QObject):
    fontsChanged=Signal();stateChanged=Signal();textCommitted=Signal()
    def __init__(self,document):
        super().__init__();self.document=document;self._font_choice='original';self._font_path='';self._editor_font_family='';self.closed=False
    def command(self,op,args,callback,**kw):callback(getattr(self.document,op)(**args))
    def update_state(self,state):self.state=state
    def set_status(self,text):pass


def subset_fixture(path,multi=False):
    pdf=fitz.open();page=pdf.new_page(width=600,height=800)
    page.insert_font(fontname='K',fontbuffer=fitz.Font('korea').buffer)
    page.insert_text((40,70),'원본 글꼴 가나다라 ABC',fontname='K',fontsize=20)
    if multi:page.insert_text((40,94),'가나다라 원본 ABC',fontname='K',fontsize=20)
    pdf.subset_fonts();pdf.save(path);pdf.close()


class InlineFontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.path=self.root/'original.pdf'
        pdf=fitz.open();p=pdf.new_page(width=600,height=800)
        p.insert_font(fontname='B',fontbuffer=fitz.Font('hebo').buffer);p.insert_font(fontname='I',fontbuffer=fitz.Font('heit').buffer)
        p.insert_text((40,70),'BOLD ',fontname='B',fontsize=20)
        p.insert_text((40+fitz.Font('hebo').text_length('BOLD ',fontsize=20),70),'italic words',fontname='I',fontsize=20)
        p.insert_text((40,400),'UNCHANGED NEIGHBOR',fontsize=12);pdf.save(self.path);pdf.close()
        self.d=Document();self.d.open(str(self.path));self.b=EditorBridge(self.d);self.e=TextEditor(self.b)
    def tearDown(self):self.e.dispose();self.d.close();self.tmp.cleanup()
    def start(self):
        target=self.d.objects(0)['blocks'][0]
        target.update(pageWidth=600,pageHeight=800,session=self.d.session,revision=self.d.revision)
        self.e.start(target);self.e.loadFonts();self.assertTrue(self.e.ready,self.e.status);return target
    def test_subset_without_unicode_cmap_is_recovered_without_new_outlines(self):
        subset_fixture(self.path);self.d.open(str(self.path));entry=self.d.pdf[0].get_fonts()[0]
        original=TTFont(BytesIO(self.d.pdf.extract_font(entry[0])[3]))
        self.assertNotIn('cmap',original)
        repaired=original_font(self.d.pdf,0,entry[3],'가나다라 원본 ABC')
        font=TTFont(BytesIO(repaired));self.assertIn('cmap',font)
        self.assertEqual(font['glyf'].compile(font),original['glyf'].compile(original))
        with self.assertRaises(ValueError):original_font(self.d.pdf,0,entry[3],'새로운 글자')
        self.start();self.assertFalse(self.e._invalid())
    def test_mixed_original_faces_and_screen_line_positions_match_saved_pdf(self):
        target=self.start();fragments=self.e._fragments()
        self.assertTrue(any('B' in text and fmt.font().bold() for pos,length,text,fmt in fragments));self.assertTrue(any('i' in text and fmt.font().italic() for pos,length,text,fmt in fragments))
        self.e.setWidth(115)
        c=QTextCursor(self.e.doc);c.movePosition(QTextCursor.End);c.insertText(' more and more text to wrap across several lines')
        self.assertGreater(self.e.height,target['rect'][3]-target['rect'][1]+40)
        expected=[];block=self.e.doc.begin()
        while block.isValid():
            layout=block.layout()
            for i in range(layout.lineCount()):
                line=layout.lineAt(i);expected.append(layout.position().y()+line.y()+line.ascent()+self.e.offset)
            block=block.next()
        data=self.e.pdf_bytes()
        with fitz.open(stream=data,filetype='pdf') as fragment:
            actual=[line['spans'][0]['origin'][1] for block in fragment[0].get_text('dict')['blocks'] for line in block.get('lines',[])]
            self.assertEqual(len(expected),len(actual))
            for a,b in zip(expected,actual):self.assertAlmostEqual(a,b,places=2)
        self.e.apply();self.assertIn('UNCHANGED NEIGHBOR',self.d.pdf[0].get_text())
        self.d.undo();self.assertEqual(self.d.pdf[0].get_text(),fitz.open(self.path)[0].get_text())
    def test_missing_new_glyph_blocks_save_without_modal_and_keeps_draft(self):
        self.start()
        self.b._font_choice='missing.ttf';self.b._font_path='missing.ttf';self.e.loadFonts()
        self.assertFalse(self.e.canApply);self.assertTrue(self.e.status)
        self.b._font_choice='original';self.b._font_path='';self.e.loadFonts()
        self.assertTrue(self.e.canApply)
        c=QTextCursor(self.e.doc);c.movePosition(QTextCursor.End);c.insertText('한글')
        self.assertFalse(self.e.canApply);self.assertIn('한',self.e.status);self.assertIn('한글',self.e.doc.toPlainText());self.assertFalse(self.d.info()['dirty'])
        chosen=self.root/'Korean.ttf';chosen.write_bytes(fitz.Font('korea').buffer)
        self.b._font_choice=str(chosen);self.b._font_path=str(chosen);self.e.loadFonts()
        self.assertTrue(self.e.canApply,self.e.status);self.e.apply();self.assertIn('한글',self.d.pdf[0].get_text())
    def test_original_character_positions_survive_edit_start_apply_and_reopen(self):
        # Distinct indents and tracking expose the 0.9.0 initial re-layout jump.
        pdf=fitz.open();page=pdf.new_page(width=600,height=800)
        page.insert_text((80,80),'TITLE with spaces',fontsize=20)
        page.insert_text((40,108),'Second line longer words',fontsize=20)
        for xref in page.get_contents():
            pdf.update_stream(xref,pdf.xref_stream(xref).replace(b'20 Tf',b'20 Tf 1.8 Tc'))
        page.insert_text((40,350),'NEIGHBOR UNCHANGED',fontsize=14)
        pdf.save(self.path);pdf.close();self.d.open(str(self.path));target=self.start()
        source=[c for line in target['textLines'] for run in line['runs'] for c in run['chars']]
        self.assertEqual(len(target['textLines']),2)
        def chars(page):
            return [c for b in page.get_text('rawdict')['blocks'] for l in b.get('lines',[]) for span in l['spans'] for c in span['chars'] if c['origin'][1]<200]
        def compare(actual,local=False,changed=False):
            self.assertEqual(len(actual),len(source))
            for i,(a,b) in enumerate(zip(source,actual)):
                if changed and i==len(source)-1:self.assertEqual(b['c'],'c')
                else:self.assertEqual(a['c'],b['c'])
                for axis in (0,1):
                    shift=target['rect'][axis] if local else 0
                    self.assertAlmostEqual(a['origin'][axis],b['origin'][axis]+shift,delta=.08)
        with fitz.open(stream=self.e.pdf_bytes(),filetype='pdf') as initial:compare(chars(initial[0]),local=True)
        # Change a real character, then inspect the PDF after actual embedding,
        # not just the editor's temporary fragment. Fractional MediaBox scaling
        # in 0.9.0 incorrectly moved the remaining characters at this stage.
        cursor=QTextCursor(self.e.doc);cursor.movePosition(QTextCursor.End)
        cursor.movePosition(QTextCursor.PreviousCharacter,QTextCursor.KeepAnchor);cursor.insertText('c')
        self.e.apply();saved=self.root/'edited.pdf';self.d.pdf.save(saved)
        with fitz.open(saved) as reopened:
            compare(chars(reopened[0]),changed=True)
            self.assertIn('NEIGHBOR UNCHANGED',reopened[0].get_text())
        self.d.undo();self.assertIn('Second line longer words',self.d.pdf[0].get_text())

    def test_no_change_preserves_original_bytes_and_ttc_localized_aliases(self):
        self.start();self.e.apply();self.assertFalse(self.d.info()['dirty'])
        a=TTFont(BytesIO(fitz.Font('korea').buffer));a['name'].setName('테스트 글꼴',4,3,1,0x412)
        collection=TTCollection();collection.fonts=[a];path=self.root/'faces.ttc';collection.save(path)
        data=font_bytes(str(path)+'#face=0');font=TTFont(BytesIO(data));self.assertIn('테스트 글꼴',names_of(font)[3])
        self.assertNotEqual(normalized('맑은 고딕'),normalized('바탕'))
        self.assertEqual(normalized('ABCDEF+맑은 고딕'),normalized('맑은고딕'))

    def test_callback_error_stale_result_timeout_and_retry_keep_original(self):
        from unittest.mock import patch
        from PySide6.QtTest import QTest
        target=self.d.objects(0)['blocks'][0];target.update(pageWidth=600,pageHeight=800)
        self.e.start(target)
        with patch.object(self.e,'_build',side_effect=ValueError('broken font layout')):
            self.e.loadFonts()
        self.assertFalse(self.e.loading);self.assertFalse(self.e._guard)
        self.assertIn('준비하지 못',self.e.status);self.assertIsNone(self.e.doc)
        self.e.retry();self.assertTrue(self.e.canApply,self.e.status)
        responses=[]
        with patch.object(self.b,'command',side_effect=lambda op,args,callback,**kw:responses.append(callback)):
            self.e.loadFonts();responses.pop()({'stale':True})
            self.assertFalse(self.e.loading);self.assertIn('바뀌',self.e.status)
            self.e.watchdog.setInterval(10);self.e.loadFonts();QTest.qWait(50)
            self.assertFalse(self.e.loading);self.assertIn('지연',self.e.status)
            responses.pop()({'fonts':[]})  # A timed-out response cannot revive the edit.
            self.assertFalse(self.e.canApply)
        self.e.watchdog.setInterval(25000);self.e.retry()
        self.assertTrue(self.e.canApply);self.assertFalse(self.d.info()['dirty'])

    def test_missing_hangul_is_previewed_and_only_new_glyphs_use_fallback(self):
        from PySide6.QtCore import QByteArray
        from PySide6.QtGui import QFontDatabase
        from bichaek.text_editor import FALLBACK
        fid=QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font('korea').buffer))
        self.start();before=[fmt.font().family() for *_,fmt in self.e._fragments()]
        cursor=QTextCursor(self.e.doc);cursor.movePosition(QTextCursor.End);cursor.insertText(' 마지막')
        self.e.timer.stop();self.e.doc.size()
        glyphs=[gid for block in [self.e.doc.begin()] for run in block.layout().glyphRuns() for gid in run.glyphIndexes()]
        self.assertNotIn(0,glyphs,'Missing Hangul must use a readable preview glyph')
        self.assertTrue(self.e.canUseFallback);self.assertFalse(self.e.canApply)
        self.e.useFallback();self.assertTrue(self.e.canApply,self.e.status)
        fragments=self.e._fragments()
        self.assertEqual(before[0],fragments[0][3].font().family())
        self.assertEqual(''.join(text for _,_,text,fmt in fragments if fmt.property(FALLBACK)),'마지막')
        self.e.apply();self.assertIn('마지막',self.d.pdf[0].get_text());self.assertIn('BOLD',self.d.pdf[0].get_text())
        QFontDatabase.removeApplicationFont(fid)

if __name__=='__main__':unittest.main()
