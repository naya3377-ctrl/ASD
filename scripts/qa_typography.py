"""Bundled font faces, fractional DPI and connected tab geometry regression.
Run with QT_SCALE_FACTOR=1, 1.25, 1.5 or 2 in separate processes.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os, sys, time, tempfile, shutil, json
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))

def main():
    from PySide6.QtCore import QUrl, QObject, Qt, QSettings, qInstallMessageHandler
    from PySide6.QtGui import QFont, QFontDatabase, QFontInfo, QRawFont
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from bichaek.ui_fonts import configure_ui_fonts
    from bichaek.bridge import Images
    from bichaek.tabs import Documents
    from bichaek.library import Library
    from bichaek.icons import Icons
    QQuickStyle.setStyle('YoonDF')
    app=QApplication([]);app.setApplicationVersion('1.0.7')
    configure_ui_fonts(app,ROOT)
    assert QFontInfo(app.font()).family()=='Pretendard'
    assert QQuickWindow.textRenderType()==QQuickWindow.QtTextRendering
    for weight in [QFont.Normal,QFont.Medium,QFont.DemiBold,QFont.Bold]:
        f=QFont(app.font());f.setWeight(weight)
        assert QFontInfo(f).family()=='Pretendard'
        raw=QRawFont.fromFont(f)
        assert raw.isValid() and all(raw.supportsCharacter(ord(c)) for c in '윤DF 읽기 주석 편집 문서 저장')
    errors=[];warnings=[]
    qInstallMessageHandler(lambda k,c,t: warnings.append(t) if 'file:' in t or 'Error' in t else None)
    images=Images();docs=Documents(images);b=docs.activeBridge
    library=Library(QSettings('YoonDF-QA','Typography'));docs.library=library
    b.setThemeMode('light');b.setAutomaticOcr(False)
    docs.showError.connect(errors.append)
    engine=QQmlApplicationEngine();engine.addImportPath(str(ROOT/'ui/style'))
    engine.addImageProvider('pages',images);engine.addImageProvider('icon',Icons(ROOT/'assets/icons'))
    for name,value in [('bridge',b),('documents',docs),('library',library),('iconTint',True)]:engine.rootContext().setContextProperty(name,value)
    engine.load(QUrl.fromLocalFile(str(ROOT/'ui/Main.qml')))
    assert engine.rootObjects(),warnings
    w=engine.rootObjects()[0]
    def items():
        todo=[w.contentItem().parentItem() or w.contentItem()]
        while todo:
            it=todo.pop()
            if it is None: continue
            yield it;todo.extend(it.childItems())
    def find(name):
        for it in items():
            if it.objectName()==name:return it
        it=w.findChild(QObject,name);assert it is not None,name
        return it
    def wait(pred):
        start=time.monotonic()
        while not pred():
            QTest.qWait(25);assert time.monotonic()-start<30,(errors,warnings[-5:])
        QTest.qWait(100)
    out=ROOT/'test-output/typography';out.mkdir(parents=True,exist_ok=True)
    scale=os.environ.get('QT_SCALE_FACTOR','1')
    checked=0; render_checked=0
    with tempfile.TemporaryDirectory(prefix='yoondf-type-') as tmp:
        try:
            paths=[]
            for title in ['속담의 구조와 기능_총칭문과 전형문.pdf','동아시아의 전신사조_형을 넘어 신을 전하는 회화미학.pdf','새 문서 디자인 검토.pdf']:
                p=Path(tmp)/title;shutil.copy2(ROOT/'samples/sample.pdf',p);paths.append(str(p))
            docs.openPaths(paths)
            wait(lambda:len(docs.tabs)==3 and all(x.document['count'] for x in docs._tabs))
            for width,height in [(1000,640),(1320,900)]:
                w.resize(width,height);QTest.qWait(250)
                header=find('readerHeader');toolbar=find('mainToolbar')
                assert toolbar.height()==56
                for name in ['readModeButton','pageViewMode','saveButton','settingsButton','moreButton']:
                    it=find(name);pos=it.mapToScene(it.boundingRect().topLeft())
                    assert pos.x()>=0 and pos.x()+it.width()<=w.width()+1,(name,pos.x(),it.width(),w.width())
                    assert it.height()>=34
                    assert it.property('font').family()=='Pretendard',(name,it.property('font').family())
                tab=find('documentTab2');assert tab.height()==48
                w.grabWindow().save(str(out/f'tabs-{width}-{scale}x.png'))
            # Verify Text and controls inherit Pretendard, including popup content.
            dialog=find('settingsDialog');dialog.open();wait(lambda:dialog.property('opened'))
            for it in items():
                if it.property('font') is not None and it.isVisible():
                    font=it.property('font')
                    if isinstance(font,QFont):
                        assert font.family()=='Pretendard',(it.objectName(),font.family())
                        checked+=1
                        if it.metaObject().indexOfProperty('renderType')>=0:
                            mode=QQmlExpression(engine.rootContext(),it,'renderType').evaluate()[0]
                            assert mode==0,(it.objectName(),mode)
                            if it.metaObject().indexOfProperty('renderTypeQuality')>=0:
                                assert it.property('renderTypeQuality')==104
                            render_checked+=1
            assert checked>30,checked
            w.grabWindow().save(str(out/f'settings-{scale}x.png'))
            dialog.close();QTest.qWait(100)
            b=docs.activeBridge;b.setThemeMode('dark');QTest.qWait(200)
            w.grabWindow().save(str(out/f'tabs-dark-{scale}x.png'))
            assert not errors,errors
            assert not warnings,warnings
            print(json.dumps({'status':'PASS','scale':scale,'devicePixelRatio':w.devicePixelRatio(),'uiFontObjects':checked,'weights':4,'renderTypeObjects':render_checked,'graphicsApi':str(w.rendererInterface().graphicsApi()),'sizes':['1000x640','1320x900']},ensure_ascii=False))
        finally:
            docs.shutdown();w.hide();engine.deleteLater();app.processEvents()
    return 0

if __name__=='__main__':sys.exit(main())
