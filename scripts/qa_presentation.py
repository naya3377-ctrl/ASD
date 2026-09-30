"""Real Qt keyboard, presentation, focus, restoration and page-fit checks.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
from pathlib import Path
import sys,time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))


def main():
    import fitz
    from unittest.mock import patch
    from PySide6.QtCore import QUrl,QObject,Qt,QPoint,QPointF,QByteArray,qInstallMessageHandler
    from PySide6.QtGui import QFontDatabase,QWheelEvent,QWindow
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from bichaek.bridge import Images
    from bichaek.tabs import Documents
    root=Path(__file__).resolve().parent.parent;out=root/'test-output';out.mkdir(exist_ok=True)
    fixture=out/'Presentation review.pdf'
    with fitz.open() as doc:
        for i in range(12):
            w,h=[(600,800),(1200,675),(600,800),(700,920)][i%4]
            p=doc.new_page(width=w,height=h)
            if i==11:continue
            p.draw_rect(fitz.Rect(0,0,w,h),color=None,fill=(.95,.96,.92))
            p.draw_rect(fitz.Rect(0,0,24,h),color=None,fill=(.15,.30,.23))
            p.insert_text((62,90),'YoonDF / PRESENTATION',fontsize=18,color=(.27,.40,.30))
            p.insert_text((62,160),f'ONE PAGE. ONE MOMENT.  /  {i+1:02}',fontsize=24,color=(.13,.25,.18))
            p.insert_text((62,205),'Read clearly. Move naturally.',fontsize=17,color=(.39,.45,.38))
            p.draw_rect(fitz.Rect(62,245,w-62,h-115),color=None,fill=(.76,.81,.65))
            p.draw_circle(fitz.Point(w*.56,h*.57),min(w,h)*.17,color=None,fill=(.37,.49,.36))
            p.insert_text((62,h-65),'ARROWS  /  PAGE UP + DOWN  /  SPACE',fontsize=12,color=(.34,.43,.34))
            if i%4==2:p.set_rotation(90)
        doc[0].insert_link({'kind':fitz.LINK_GOTO,'from':fitz.Rect(62,230,230,280),'page':7,'to':fitz.Point(0,0)})
        doc[0].insert_link({'kind':fitz.LINK_URI,'from':fitz.Rect(62,290,230,330),'uri':'https://example.com/yoondf'})
        doc.save(fixture)
    QQuickStyle.setStyle(os.environ.get('YOONDF_QA_STYLE','Basic'));app=QApplication([])
    QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font('korea').buffer))
    warnings=[]
    def message(kind,context,text):
        if 'file:' in text or 'ReferenceError' in text or 'TypeError' in text:warnings.append(text)
    qInstallMessageHandler(message)
    images=Images();documents=Documents(images);b=documents.activeBridge
    saved_auto=b.automaticOcr;b.setAutomaticOcr(False)
    errors=[];documents.showError.connect(errors.append)
    engine=QQmlApplicationEngine();engine.addImageProvider('pages',images)
    engine.rootContext().setContextProperty('bridge',b)
    engine.rootContext().setContextProperty('documents',documents)
    engine.load(QUrl.fromLocalFile(str(root/'ui/Main.qml')))
    assert engine.rootObjects(),warnings
    window=engine.rootObjects()[0];window.setProperty('uiFontFamily','Droid Sans Fallback')
    def wait(predicate,timeout=20):
        start=time.monotonic()
        while not predicate():
            app.processEvents();QTest.qWait(15)
            if time.monotonic()-start>timeout:raise AssertionError(('timeout',errors,warnings,b.currentPage,window.property('presenting'),window.property('restoring')))
        app.processEvents();QTest.qWait(70)
    def item(name):
        obj=window.findChild(QObject,name)
        if obj is not None:return obj
        pending=[window.contentItem()]
        while pending:
            obj=pending.pop()
            if obj.objectName()==name:return obj
            pending.extend(obj.childItems())
        raise AssertionError(name)
    def settled():return not window.property('restoring') and not window.property('switching')
    def key(code,mods=Qt.NoModifier):QTest.keyClick(window,code,mods)
    def page(number):wait(lambda:b.currentPage==number and settled())
    def click(name):
        obj=item(name);QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,obj.mapToScene(obj.boundingRect().center()).toPoint());QTest.qWait(80)
    def fit():
        paper=item('presentationPaper');view=item('presentationView')
        assert 0<=paper.x() and 0<=paper.y()
        assert paper.x()+paper.width()<=view.width()+.1 and paper.y()+paper.height()<=view.height()+.1
        assert abs(paper.height()/paper.width()-b.pageRatio(b.currentPage))<.001
    try:
        documents.openPaths([str(fixture)])
        wait(lambda:b.document['count']==12 and b.imageUrl(0,'main') and settled())
        item('pageList').forceActiveFocus()
        for code,target in [(Qt.Key_Right,1),(Qt.Key_Down,2),(Qt.Key_Left,1),(Qt.Key_Up,0),(Qt.Key_PageDown,1),(Qt.Key_PageUp,0),(Qt.Key_Space,1)]:key(code);page(target)
        key(Qt.Key_Space,Qt.ShiftModifier);page(0)
        for i in range(5):key(Qt.Key_Right)
        page(5)
        key(Qt.Key_End);page(11);key(Qt.Key_Right);page(11)
        key(Qt.Key_Home);page(0);key(Qt.Key_Left);page(0)
        print('PASS: reader arrows/Page Up/Down/Space/Shift+Space, rapid presses, Home/End and boundaries',flush=True)
        # Focus protects text input, including spaces and cursor movement.
        key(Qt.Key_F,Qt.ControlModifier);search=item('searchInput')
        search.setProperty('text','AB');search.setProperty('cursorPosition',1)
        key(Qt.Key_Right);key(Qt.Key_Space);key(Qt.Key_Home);key(Qt.Key_End);key(Qt.Key_PageDown)
        assert b.currentPage==0 and search.property('text')=='AB ',search.property('text')
        search.setProperty('text','');window.setProperty('pendingQuery','');b.search('');QTest.qWait(350)
        inp=item('pageNumberInput');inp.forceActiveFocus();inp.setProperty('text','4')
        key(Qt.Key_Left);assert b.currentPage==0
        key(Qt.Key_Return);page(3);key(Qt.Key_Right);page(4)
        b.composeComment(4,70,70);wait(lambda:item('annotationEditor').property('visible'))
        item('commentBody').setProperty('text','Draft remains here')
        for code in [Qt.Key_Left,Qt.Key_Down,Qt.Key_PageDown,Qt.Key_End,Qt.Key_F5]:key(code)
        assert b.currentPage==4 and not window.property('presenting')
        key(Qt.Key_Escape);wait(lambda:not item('annotationEditor').property('visible'))
        assert not b.document['dirty']
        print('PASS: search field, page-number entry and comment dialog keep their own keys; modal F5 blocked',flush=True)
        # Enter/exit without advancing restores position, zoom and panel choice.
        window.setProperty('commentsOpen',True);window.setProperty('zoom',1.2)
        item('pageList').forceActiveFocus();key(Qt.Key_Home);page(0)
        pages=item('pageList');pages.setProperty('contentY',120.0);QTest.qWait(150)
        before_y=pages.property('contentY');before_page=b.currentPage
        before_offset=-item('paper'+str(before_page)).mapToItem(pages,QPointF(0,0)).y()/item('paper'+str(before_page)).width()
        old_size=(window.width(),window.height());old_visibility=window.visibility()
        key(Qt.Key_F5);wait(lambda:window.property('presenting') and b.imageUrl(b.currentPage,'presentation'))
        assert window.visibility()==QWindow.FullScreen
        assert all(not item(n).property('visible') for n in ['readerHeader','readerWorkspace','readerFooter'])
        fit();assert b._presentation_active
        key(Qt.Key_Tab,Qt.ControlModifier);assert documents.activeIndex==0
        key(Qt.Key_Escape);wait(settled)
        assert not window.property('presenting') and not b._presentation_active
        assert window.property('commentsOpen') and window.property('zoom')==1.2
        assert window.visibility()==old_visibility and (window.width(),window.height())==old_size
        after_offset=-item('paper'+str(b.currentPage)).mapToItem(pages,QPointF(0,0)).y()/item('paper'+str(b.currentPage)).width()
        assert b.currentPage==before_page and abs(after_offset-before_offset)<.005,(before_page,b.currentPage,before_y,pages.property('contentY'),before_offset,after_offset)
        print('PASS: fullscreen chrome hiding, bounded fit, normal geometry/panel/zoom/position restoration',flush=True)
        # Slideshow uses the same page position, but never scrolls the hidden reader.
        key(Qt.Key_Home);page(0)
        key(Qt.Key_L,Qt.ControlModifier);wait(lambda:window.property('presenting'))
        for code,target in [(Qt.Key_Right,1),(Qt.Key_Down,2),(Qt.Key_Left,1),(Qt.Key_PageDown,2),(Qt.Key_Space,3)]:
            key(code);page(target);wait(lambda:b.imageUrl(target,'presentation'));fit()
        key(Qt.Key_Space,Qt.ShiftModifier);page(2)
        key(Qt.Key_End);page(11);key(Qt.Key_Down);page(11)
        key(Qt.Key_Home);page(0);key(Qt.Key_Up);page(0)
        # Mouse, fractional wheel and multi-detent wheel map to whole pages.
        surface=item('presentationSurface');pos=surface.mapToScene(QPointF(8,100))
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,pos.toPoint());page(1)
        QTest.mouseClick(window,Qt.RightButton,Qt.NoModifier,pos.toPoint());page(0)
        def wheel(angle):
            event=QWheelEvent(pos,window.mapToGlobal(pos),QPoint(),QPoint(0,angle),Qt.NoButton,Qt.NoModifier,Qt.ScrollUpdate,False)
            app.sendEvent(window,event);app.processEvents()
        wheel(-60);assert b.currentPage==0
        wheel(-60);page(1);wheel(-360);page(4)
        key(Qt.Key_Home);page(0);wait(lambda:len(b.textLayout(0).get('links',[]))==2)
        def link_point(x,y):
            p=item('presentationPaper');s=p.width()/b.pageWidth(0)
            return p.mapToScene(QPointF(x*s,y*s)).toPoint()
        with patch('PySide6.QtGui.QDesktopServices.openUrl',return_value=True) as opened:
            QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,link_point(100,310));QTest.qWait(80)
            assert opened.call_count==1 and b.currentPage==0
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,link_point(100,250));page(7)
        key(Qt.Key_F11);wait(settled);assert not window.property('presenting') and b.currentPage==7
        print('PASS: presentation keyboard/mouse/wheel, portrait/landscape/rotation fit, PDF links, exit at shown page',flush=True)
        # Pending search results and automatic OCR must not disturb a presentation.
        b.search('YoonDF')
        key(Qt.Key_F5);wait(lambda:window.property('presenting'))
        wait(lambda:not b.searching);assert b.currentPage==7
        b._auto_ocr=True
        key(Qt.Key_End);page(11);wait(lambda:11 in b._text_layouts)
        with patch.object(b,'startOcr') as ocr:
            b.auto_recognize();QTest.qWait(1100);assert not ocr.called
        b._auto_ocr=False
        key(Qt.Key_Home);page(0);wait(lambda:b.imageUrl(0,'presentation'))
        item('presentationView').setProperty('controlsVisible',True)
        window.grabWindow().save(str(out/'presentation-060.png'))
        click('exitPresentationButton');wait(settled)
        window.setProperty('workspaceMode','read');window.setProperty('searchOpen',False);window.setProperty('zoom',.72)
        QTest.qWait(700);window.grabWindow().save(str(out/'reader-060.png'))
        # Returning to editing reloads blocks for the page actually shown.
        window.setProperty('workspaceMode','edit');window.setProperty('tool','editText')
        key(Qt.Key_F5);wait(lambda:window.property('presenting'));key(Qt.Key_Right);page(1)
        key(Qt.Key_Escape);wait(lambda:settled() and len(b.blocks)>0)
        assert window.property('tool')=='editText' and window.property('workspaceMode')=='edit'
        window.setProperty('workspaceMode','read');window.setProperty('tool','read')
        # Maximized readers return maximized; a new blank tab cannot present.
        window.showMaximized();QTest.qWait(100);key(Qt.Key_F5);wait(lambda:window.property('presenting'))
        key(Qt.Key_Escape);wait(settled);assert window.visibility()==QWindow.Maximized
        documents.newTab();wait(settled);key(Qt.Key_F5);assert not window.property('presenting')
        assert not errors,errors
        assert not warnings,warnings
        print('PASS: pending search navigation/automatic OCR suspension, maximized restoration, blank-document guard; no QML warnings',flush=True)
    finally:
        b.setAutomaticOcr(saved_auto)
        window.setVisible(False);documents.shutdown();del engine;qInstallMessageHandler(None)

if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support();main()
