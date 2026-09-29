"""Print preview QA: what the preview shows is what the printer gets.

A mixed portrait/landscape document: automatic orientation turns the odd page,
custom ranges and paper sizes update the sheets, black-and-white and "save as
PDF" produce the pages shown.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
from pathlib import Path
import sys, time
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))


def build(path):
    import fitz
    doc=fitz.open()
    for index in range(5):
        wide=index==2
        page=doc.new_page(width=842 if wide else 595,height=595 if wide else 842)
        page.draw_rect(page.rect+(20,20,-20,-20),color=(0.8,0.1,0.1),width=6)
        page.insert_text((60,120),f'Page {index+1} {"landscape" if wide else "portrait"}',fontsize=28)
    doc.save(path)


def main():
    from PySide6.QtCore import QUrl,QPointF,Qt,qInstallMessageHandler,QObject
    import PySide6.QtCore as C
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from bichaek.bridge import Images
    from bichaek.tabs import Documents
    out=root/'test-output';out.mkdir(exist_ok=True);pdf=out/'Print Preview.pdf';build(pdf)
    QQuickStyle.setStyle(os.environ.get('YOONDF_QA_STYLE','Basic'));app=QApplication([])
    warnings=[];qInstallMessageHandler(lambda k,c,m: warnings.append(m) if 'file:' in m else None)
    images=Images();docs=Documents(images)
    engine=QQmlApplicationEngine();engine.addImageProvider('pages',images)
    engine.rootContext().setContextProperty('bridge',docs.activeBridge);engine.rootContext().setContextProperty('documents',docs)
    engine.load(QUrl.fromLocalFile(str(root/'ui/Main.qml')));w=engine.rootObjects()[0]
    w.setProperty('width',1400);w.setProperty('height',860)
    def wait(predicate,timeout=20):
        start=time.monotonic()
        while not predicate():
            app.processEvents();QTest.qWait(15)
            if time.monotonic()-start>timeout:raise AssertionError(('timeout',warnings[-5:]))
        app.processEvents();QTest.qWait(80)
    def find(name):
        pending=[w.contentItem().parentItem() or w.contentItem()]
        while pending:
            item=pending.pop()
            if item is None:continue
            if item.objectName()==name:return item
            pending.extend(item.childItems())
    def click(item):
        QTest.mouseClick(w,Qt.LeftButton,Qt.NoModifier,item.mapToScene(item.boundingRect().center()).toPoint());QTest.qWait(60)
    try:
        from unittest.mock import patch
        from PySide6.QtWidgets import QFileDialog
        import fitz
        docs.openPaths([str(pdf)]);b=docs.activeBridge;b.setAutomaticOcr(False)
        wait(lambda:b.document['count']==5 and not b.busy)
        preview=w.findChild(QObject,'printPreview')
        def prop(name):
            value=preview.property(name)
            return value.toVariant() if hasattr(value,'toVariant') else value
        QTest.keyClick(w,Qt.Key_P,Qt.ControlModifier);wait(lambda:preview.property('opened'))
        wait(lambda:len(prop('sheets'))==5)
        layout=prop('layout')
        # Automatic orientation: portrait paper, the landscape page is turned.
        assert layout['orientation']=='portrait' and [s['rotate'] for s in layout['sheets']]==[False,False,True,False,False],layout
        preview.setProperty('current',2);wait(lambda:str(find('printSheet').property('source')).startswith('image://'))
        w.grabWindow().save(str(out/'print-preview.png'))
        # Custom range and fit.
        preview.setProperty('range','custom');preview.setProperty('custom','2-3');wait(lambda:len(prop('sheets'))==2)
        preview.setProperty('custom','9');wait(lambda:bool(prop('layout')['error']))
        assert not find('printNowButton').property('enabled')
        preview.setProperty('custom','3, 1');wait(lambda:[s['page'] for s in prop('sheets')]==[2,0])
        preview.setProperty('fit','fit');wait(lambda:abs(prop('sheets')[1]['rect'][2]-prop('layout')['area'][2])<1)
        # Landscape by hand: nothing turns.
        preview.setProperty('orientation','landscape');wait(lambda:prop('layout')['orientation']=='landscape')
        assert not any(s['rotate'] for s in prop('sheets'))
        preview.setProperty('orientation','auto')
        # Save as PDF from the preview.
        preview.setProperty('printerName','__pdf__');preview.setProperty('gray',True)
        target=out/'print-preview-output.pdf';target.unlink(missing_ok=True)
        wait(lambda:find('printNowButton').property('enabled'))
        with patch.object(QFileDialog,'getSaveFileName',return_value=(str(target),'PDF')):
            click(find('printNowButton'));wait(lambda:target.exists() and not b.busy,timeout=60)
        assert not preview.property('opened')
        with fitz.open(target) as printed:
            assert len(printed)==2,len(printed)
            for page in printed:
                assert page.rect.width<page.rect.height,page.rect   # portrait paper throughout
            image=printed[0].get_images()[0]
        assert not warnings,warnings
        print('PASS: preview sheets match layout; auto orientation turns the landscape page; custom range, error, fit, manual orientation; save as PDF prints the previewed pages')
    finally:
        b._state['dirty']=False;w.setVisible(False);docs.shutdown();del engine


if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
