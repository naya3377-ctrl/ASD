"""Production-style UI, brand and no-motion thumbnail regression, 1.0.7.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os, sys, time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))

def main():
    import fitz
    from PySide6.QtCore import QUrl,QObject,Qt,QByteArray,QSettings,qInstallMessageHandler
    from PySide6.QtGui import QFontDatabase,QIcon
    from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from bichaek.bridge import Images
    from bichaek.tabs import Documents
    from bichaek.library import Library
    from bichaek.icons import Icons
    QQuickStyle.setStyle('YoonDF')
    app=QApplication([]);app.setApplicationVersion('1.0.7')
    QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font('korea').buffer))
    from bichaek.ui_fonts import configure_ui_fonts
    configure_ui_fonts(app,ROOT)
    errors=[];warnings=[]
    qInstallMessageHandler(lambda k,c,t: warnings.append(t) if 'file:' in t or 'Error' in t else None)
    images=Images();docs=Documents(images);b=docs.activeBridge
    library=Library(QSettings('YoonDF-QA','Polish'));docs.library=library
    b.setThemeMode('light');b.setReducedMotion(False);b.setAutomaticOcr(False)
    docs.showError.connect(errors.append)
    engine=QQmlApplicationEngine();engine.addImportPath(str(ROOT/'ui/style'))
    engine.addImageProvider('pages',images);engine.addImageProvider('icon',Icons(ROOT/'assets/icons'))
    for name,value in [('bridge',b),('documents',docs),('library',library),('iconTint',True)]:engine.rootContext().setContextProperty(name,value)
    engine.load(QUrl.fromLocalFile(str(ROOT/'ui/Main.qml')))
    assert engine.rootObjects(),warnings
    w=engine.rootObjects()[0];w.setProperty('uiFontFamily','Pretendard')
    out=ROOT/'test-output/polish';out.mkdir(parents=True,exist_ok=True)
    def wait(pred,seconds=30):
        start=time.monotonic()
        while not pred():
            QTest.qWait(20)
            assert time.monotonic()-start<seconds,(errors,warnings[-10:])
        QTest.qWait(30)
    def find(name):
        todo=[w.contentItem().parentItem() or w.contentItem()]
        while todo:
            item=todo.pop()
            if item is None:continue
            if item.objectName()==name:return item
            todo.extend(item.childItems())
        item=w.findChild(QObject,name);assert item is not None,name
        return item
    def click(name):
        it=find(name);QTest.mouseClick(w,Qt.LeftButton,Qt.NoModifier,it.mapToScene(it.boundingRect().center()).toPoint())
    try:
        icon=QIcon(str(ROOT/'assets/icon.ico'))
        assert not icon.isNull()
        for size in (16,24,32,48,64,128,256):assert not icon.pixmap(size,size).isNull()
        QTest.qWait(450)
        logo=find('welcomeLogo');assert logo.property('source').toString().endswith('/icon.png') and logo.opacity()==1 and logo.scale()==1
        w.grabWindow().save(str(out/'start-light.png'))
        # Every built-in control uses the production YoonDF style, not Basic.
        click('settingsButton');dialog=find('settingsDialog');wait(lambda:dialog.property('opened'))
        assert dialog.property('opacity')==1
        switch=find('reducedMotionSwitch');assert switch.isVisible()
        click('reducedMotionSwitch');wait(lambda:b.reducedMotion)
        b.preferences.sync();assert QSettings('Bichaek','BichaekPDF').value('reducedMotion',False,type=bool)
        choice=find('themeChoice');click('themeChoice');QTest.qWait(100)
        assert QQmlExpression(engine.rootContext(),choice,'popup.opened').evaluate()[0]
        QTest.keyClick(w,Qt.Key_Escape);QTest.qWait(100)
        w.grabWindow().save(str(out/'settings-light.png'))
        dialog.close();wait(lambda:not dialog.property('visible'))
        for width,height in [(1000,640),(1320,900)]:
            w.resize(width,height);QTest.qWait(100)
            click('settingsButton');wait(lambda:dialog.property('opened'))
            assert 0<=dialog.property('y') and dialog.property('height')<=w.height()
            dialog.close();wait(lambda:not dialog.property('visible'))
        b.setReducedMotion(False)
        docs.openPaths([str(ROOT/'samples/sample.pdf')]);b=docs.activeBridge;b.setAutomaticOcr(False)
        wait(lambda:b.document['count']==4 and bool(b.imageUrl(0,'thumb')))
        thumbs=find('thumbnailList');assert thumbs.property('highlightMoveDuration')==0
        assert thumbs.property('highlightResizeDuration')==0
        assert b.selection==[],b.selection
        assert find('thumbnailCurrentMarker0').isVisible()
        assert not find('thumbnailSelectionFrame0').isVisible()
        w.goPage(1);wait(lambda:b.currentPage==1 and not w.property('restoring'))
        assert b.selection==[] and find('thumbnailCurrentMarker1').isVisible()
        assert not find('thumbnailSelectionFrame1').isVisible()
        w.grabWindow().save(str(out/'marker-only.png'))
        before=b.currentPage
        click('thumbnailPaper1');wait(lambda:b.currentPage==1)
        assert b.selection==[1],b.selection
        frame=find('thumbnailSelectionFrame1');paper=find('thumbnailPaper1')
        assert frame.isVisible() and frame.width()==paper.width() and frame.height()==paper.height()
        assert frame.x()==0 and frame.y()==0
        w.grabWindow().save(str(out/'paper-selection.png'))
        # Current-page navigation and reading do not create or move selections.
        w.goPage(2);wait(lambda:b.currentPage==2 and not w.property('restoring'))
        assert b.selection==[1] and not find('thumbnailSelectionFrame2').isVisible()
        assert find('thumbnailCurrentMarker2').isVisible()
        b.selectPage(1,True,False);QTest.qWait(100)
        assert b.selection==[] and not frame.isVisible()
        b.update_state(dict(b.document));QTest.qWait(100)
        assert b.selection==[],b.selection
        click('thumbnailPaper1');wait(lambda:b.selection==[1])
        preview=find('thumbnailImage1');paper=find('thumbnailPaper1')
        # The image/geometry have no fade, slide or zoom between frames.
        states=[]
        for _ in range(8):
            states.append((paper.width(),paper.height(),paper.scale(),paper.opacity(),preview.opacity(),preview.scale()))
            QTest.qWait(20)
        assert len(set(states))==1 and states[0][2:]==(1,1,1,1),states
        w.grabWindow().save(str(out/'reader-light.png'))
        b.setThemeMode('dark');QTest.qWait(250)
        w.grabWindow().save(str(out/'reader-dark.png'))
        click('settingsButton');wait(lambda:dialog.property('opened'))
        w.grabWindow().save(str(out/'settings-dark.png'))
        dialog.close();wait(lambda:not dialog.property('visible'))
        assert not errors,errors
        assert not warnings,warnings
        print('PASS: approved brand/ICO sizes, production custom controls, startup motion, reduced-motion persistence, light/dark, 1000x640/1320x900, immediate static thumbnail selection; no QML warnings')
    finally:
        b.setThemeMode('light');b.setReducedMotion(False)
        for bridge in docs._tabs:bridge._state['dirty']=False
        w.setVisible(False);docs.shutdown();del engine;qInstallMessageHandler(None)

if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support();main()
