"""Actual QML/IME editing latency, repeated apply/save, and draft lifecycle QA.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os,sys,time,json,statistics
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
root=Path(os.environ.get('YOONDF_QA_SOURCE',Path(__file__).resolve().parent.parent))
sys.path.insert(0,str(root))

def main():
    import fitz
    from PySide6.QtCore import QUrl,QObject,Qt,QByteArray,QTimer,qInstallMessageHandler
    from PySide6.QtGui import QFontDatabase,QInputMethodEvent,QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from bichaek.bridge import Images
    from bichaek.tabs import Documents
    out=root/'test-output';out.mkdir(exist_ok=True);source=out/'Dense Korean Editing.pdf'
    pdf=fitz.open();p=pdf.new_page(width=600,height=840);p.insert_font(fontname='K',fontbuffer=fitz.Font('korea').buffer)
    text='고정수의 작업은 사람과 자연의 관계를 표현한다. '
    for col in (38,312):
        for i in range(40):p.insert_text((col,50+i*12),text,fontname='K',fontsize=9)
    pdf.subset_fonts();pdf.save(source);pdf.close()
    QQuickStyle.setStyle(os.environ.get('YOONDF_QA_STYLE','Basic'));app=QApplication([])
    QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font('korea').buffer))
    warnings=[];qInstallMessageHandler(lambda k,c,t:warnings.append(t) if 'file:' in t or 'ReferenceError' in t or 'TypeError' in t else None)
    images=Images();documents=Documents(images);b=documents.activeBridge;auto=b.automaticOcr;b.setAutomaticOcr(False)
    errors=[];documents.showError.connect(errors.append)
    engine=QQmlApplicationEngine();engine.addImageProvider('pages',images)
    engine.rootContext().setContextProperty('bridge',b);engine.rootContext().setContextProperty('documents',documents)
    engine.load(QUrl.fromLocalFile(str(root/'ui/Main.qml')));assert engine.rootObjects(),warnings
    w=engine.rootObjects()[0];w.resize(1700,1040);w.setProperty('uiFontFamily','Droid Sans Fallback')
    def wait(pred,timeout=30):
        start=time.monotonic()
        while not pred():
            app.processEvents();QTest.qWait(10)
            assert time.monotonic()-start<timeout,(errors,warnings[-8:],b.liveEditor.status)
    def item(name):
        pending=[w.contentItem()]
        while pending:
            obj=pending.pop()
            if obj.objectName()==name:return obj
            pending.extend(obj.childItems())
        found=w.findChild(QObject,name);assert found is not None,name
        return found
    def click(name):
        obj=item(name);QTest.mouseClick(w,Qt.LeftButton,Qt.NoModifier,obj.mapToScene(obj.boundingRect().center()).toPoint())
        app.processEvents()
    jobs=[];real=b.command
    def track(op,*args,**kw):
        if op=='editor_fonts':jobs.append(time.monotonic())
        return real(op,*args,**kw)
    b.command=track
    gaps=[];last=[time.monotonic()]
    beat=QTimer();beat.setInterval(10)
    def pulse():
        now=time.monotonic();gaps.append(now-last[0]);last[0]=now
    beat.timeout.connect(pulse);beat.start()
    starts=[];typing=[];settles=[];applies=[]
    try:
        documents.openPaths([str(source)])
        wait(lambda:b.document['count']==1 and not b.busy and not w.property('restoring'))
        click('editModeButton');wait(lambda:b.blocksAt(0));original=len(b.blocksAt(0)[0]['text'])
        for turn in range(8):
            b.loadBlocks(0);wait(lambda:b.blocksAt(0));block=max(b.blocksAt(0),key=lambda x:len(x['text']))
            started=time.monotonic();b.editBlock(block);wait(lambda:b.liveEditor.ready and not b.liveEditor.loading)
            app.processEvents();starts.append(time.monotonic()-started)
            field=item('replacementText');field.forceActiveFocus();QTest.keyClick(w,Qt.Key_End,Qt.ControlModifier)
            before=b.liveEditor.doc.toPlainText();initial_height=b.liveEditor.height;added=(' 사람과 자연' if os.environ.get('YOONDF_QA_EXISTING_ONLY') else (' 마지막 편집을 확인합니다.' if turn==0 else ' 원본'))
            for ch in added:
                event=QInputMethodEvent();event.setCommitString(ch)
                started=time.monotonic();QGuiApplication.sendEvent(w.focusObject(),event);app.processEvents();typing.append(time.monotonic()-started)
                QTest.qWait(12)
            assert abs(b.liveEditor.doc.textWidth()-b.liveEditor.width)<.01, 'TextArea must not shrink the editing width on input'
            assert b.liveEditor.doc.begin().layout().lineCount()==1, 'Untouched original lines must not rewrap when typing elsewhere'
            started=time.monotonic();wait(lambda:b.liveEditor.canApply,timeout=35);settles.append(time.monotonic()-started)
            assert b.liveEditor.doc.toPlainText()==before+added
            assert b.liveEditor.height-initial_height<50, 'Short insertion must not double the whole paragraph'
            print('PASS round',turn+1,'type/apply/save/reopen',flush=True)
            if turn==0:w.grabWindow().save(str(out/'YoonDF-0.9.4-editing.png'))
            started=time.monotonic();click('applyTextButton');wait(lambda:not b.busy and not item('textEditorSession').property('visible'));applies.append(time.monotonic()-started)
            b.save(False);wait(lambda:not b.busy and not b.document['dirty'])
            with fitz.open(source) as saved:assert ''.join(added.split()) in ''.join(saved[0].get_text().split())
        b.loadBlocks(0);wait(lambda:b.blocksAt(0));b.editBlock(b.blocksAt(0)[0]);wait(lambda:b.liveEditor.ready)
        w.close();wait(lambda:item('draftCloseDialog').property('visible'));click('continueEditing')
        assert item('textEditorSession').property('visible');click('cancelTextButton');wait(lambda:not item('textEditorSession').property('visible'))
        assert not errors and not warnings,(errors,warnings)
        result={'block_characters':original,'rounds':len(starts),'start_seconds':starts,'key_median_ms':statistics.median(typing)*1000,'key_p95_ms':sorted(typing)[int(len(typing)*.95)]*1000,'key_max_ms':max(typing)*1000,'font_settle_seconds':settles,'apply_seconds':applies,'gui_max_gap_ms':max(gaps)*1000,'font_requests':len(jobs),'registered_fonts':len(b.liveEditor.ids),'warnings':warnings}
        (out/'editing-performance.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
    finally:
        beat.stop();b.setAutomaticOcr(auto);w.setVisible(False);documents.shutdown();del engine;qInstallMessageHandler(None)

if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support();main()
