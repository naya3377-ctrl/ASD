"""Regressions for cached validation, IME composition and engine loss."""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
import fitz
from bichaek.document import Document
from bichaek.text_editor import TextEditor,FALLBACK
from tests.test_inline_fonts import EditorBridge,subset_fixture

class EditStabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'subset.pdf';subset_fixture(self.path,multi=True)
        self.d=Document();self.d.open(str(self.path));self.b=EditorBridge(self.d);self.e=TextEditor(self.b)
        target=self.d.objects(0)['blocks'][0];target.update(pageWidth=600,pageHeight=800,session=self.d.session,revision=self.d.revision)
        self.e.start(target);self.e.loadFonts();assert self.e.ready,self.e.status
    def tearDown(self):self.e.dispose();self.d.close();self.temp.cleanup()
    def append(self,text,original=True):
        cursor=QTextCursor(self.e.doc)
        fmt=cursor.charFormat();cursor.movePosition(QTextCursor.End)
        if original:cursor.setCharFormat(fmt)
        cursor.insertText(text);self.e.timer.stop()
    def test_property_reads_reuse_validation_and_font_loading(self):
        self.assertTrue(self.e.canApply)
        with patch.object(self.e,'_fragments',wraps=self.e._fragments) as scan:
            for _ in range(200):self.e.canApply;self.e.canUseFallback
            self.assertEqual(scan.call_count,0)
        with patch.object(self.e,'_register',wraps=self.e._register) as register:
            self.e.loadFonts();self.assertTrue(self.e.canApply)
            self.assertEqual(len(self.e.ids),len(self.e._registered))
    def test_new_letters_reuse_fallback_and_never_reformat_original(self):
        original_family=self.e._fragments()[0][3].font().family()
        with patch.object(self.b,'command',wraps=self.b.command) as command, patch.object(self.e,'_reformat',side_effect=AssertionError('whole block reformatted')):
            self.append(' 마지막');self.e.useFallback(True);self.assertTrue(self.e.canApply,self.e.status)
            self.append(' 편집');self.e.useFallback(True);self.assertTrue(self.e.canApply,self.e.status)
            self.append(' 마지막');self.e.useFallback(True);self.assertTrue(self.e.canApply,self.e.status)
            self.assertEqual(command.call_count,1)
        self.assertEqual(self.e._fragments()[0][3].font().family(),original_family)
        self.e.apply();self.assertIn('마지막',self.d.pdf[0].get_text());self.assertIn('편집',self.d.pdf[0].get_text())
    def test_latin_only_korean_named_font_falls_back_to_glyph_coverage(self):
        latin=Path(self.temp.name)/'Korean-Regular.ttf';latin.write_bytes(fitz.Font('helv').buffer)
        self.b.fallback_font_path=lambda:str(latin)
        self.append(' 마지막');self.e.useFallback(True)
        self.assertTrue(self.e.canApply,self.e.status)
        self.e.apply();self.assertIn('마지막',self.d.pdf[0].get_text())
    def test_font_result_waits_for_ime_composition_and_cancel_drops_it(self):
        self.append(' 마지막');pending=[]
        def capture(op,args,callback,**kw):pending.append((args,callback))
        with patch.object(self.b,'command',side_effect=capture):self.e.useFallback(True)
        args,callback=pending.pop();result=self.d.editor_fonts(**args)
        self.e.setComposing(True);before=self.e.doc.toPlainText();callback(result)
        self.assertIsNotNone(self.e._pending_font);self.assertFalse(self.e.canApply)
        self.assertFalse(any(fmt.property(FALLBACK) for *_,fmt in self.e._fragments()))
        self.e.setComposing(False);QTest.qWait(30)
        self.assertTrue(self.e.canApply,self.e.status);self.assertEqual(self.e.doc.toPlainText(),before)
        self.e.setComposing(True);self.e.loadFonts()
        self.assertIsNotNone(self.e._pending_font)
        self.e.stop();self.e.setComposing(False);QTest.qWait(30)
        self.assertFalse(self.e.ready);self.assertIsNone(self.e._pending_font)
    def test_composing_keeps_new_text_without_launching_font_work(self):
        self.e.setComposing(True)
        with patch.object(self.b,'command',wraps=self.b.command) as command:
            self.append(' 마지막');self.e.useFallback(True);QTest.qWait(250)
            self.assertEqual(command.call_count,0)
        self.e.setComposing(False);self.e.timer.stop();self.e.useFallback(True)
        self.assertTrue(self.e.canApply)
    def test_unsupported_character_does_not_loop_and_deletion_recovers(self):
        self.append('\U0010ffff');self.e.useFallback(True)
        self.assertFalse(self.e.canApply)
        with patch.object(self.b,'command',wraps=self.b.command) as command:
            for _ in range(5):self.e.useFallback(True)
            self.assertEqual(command.call_count,0)
        cursor=QTextCursor(self.e.doc);cursor.movePosition(QTextCursor.End);cursor.deletePreviousChar()
        self.assertTrue(self.e.canApply,self.e.status)

class WorkerFailureTests(unittest.TestCase):
    def test_real_worker_exit_finishes_pending_requests_without_losing_draft(self):
        from bichaek.tabs import Documents
        from bichaek.rendering import Images
        app=QApplication.instance() or QApplication([]);docs=Documents(Images());b=docs.activeBridge
        errors=[];docs.showError.connect(errors.append)
        try:
            # A stopped native worker must not leave font/apply callbacks busy forever.
            b.liveEditor._status='draft';b._busy=True
            failed=[];docs.hub.callbacks[999]=(b,None,failed.append)
            docs.hub.process.terminate();docs.hub.process.join(timeout=3);docs.hub.poll()
            self.assertTrue(docs.hub.failed);self.assertFalse(b.busy);self.assertTrue(failed);self.assertTrue(errors)
            self.assertFalse(b.liveEditor.canApply)
            b.command('editor_fonts',{},lambda x:None,error_callback=failed.append);QTest.qWait(25)
            self.assertEqual(len(failed),2)
            # Simulate an in-flight payload stranded in a dead worker's pipe.
            docs.hub.inbox.put({'id':1000,'op':'abandoned','args':{'data':b'x'*(1024*1024)}})
            QTest.qWait(25)
        finally:docs.shutdown()

if __name__=='__main__':unittest.main()
