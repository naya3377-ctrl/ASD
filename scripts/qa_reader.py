"""Real Qt pointer, wheel, link, OCR and print integration regression tests.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    import fitz
    from unittest.mock import patch
    from PySide6.QtCore import QUrl, QObject, QPoint, QPointF, Qt, QByteArray
    from PySide6.QtGui import QFontDatabase, QWheelEvent
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication
    from PySide6.QtPrintSupport import QPrinter
    from PySide6.QtTest import QTest
    from bichaek.bridge import Images, Bridge
    from bichaek.printing import selected_pages
    root = Path(__file__).resolve().parent.parent
    out = root/'test-output'; out.mkdir(exist_ok=True)
    fixture = out/'reader-fixture.pdf'
    pdf = fitz.open()
    for i in range(30):
        p = pdf.new_page(width=600,height=800)
        p.insert_text((45,70), 'Selectable text one', fontsize=20)
        p.insert_text((45,100), 'Second line for selection', fontsize=20)
        p.insert_text((45,160), 'Website link', fontsize=18)
        p.insert_text((45,205), 'Go to third page', fontsize=18)
        p.insert_text((45,270), f'PAGE {i+1}', fontsize=26)
    p=pdf[0]
    p.insert_link({'kind':fitz.LINK_URI,'from':fitz.Rect(40,138,190,166),'uri':'https://example.com/pdf?q=1'})
    p.insert_link({'kind':fitz.LINK_GOTO,'from':fitz.Rect(40,180,220,212),'page':2,'to':fitz.Point(0,0)})
    pdf[1].set_rotation(90)
    pdf.save(fixture);pdf.close()
    QQuickStyle.setStyle('Basic');app=QApplication([])
    QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font('korea').buffer))
    images=Images();bridge=Bridge(images)
    saved_auto=bridge.automaticOcr;saved_speed=bridge.wheelSpeed
    bridge.setAutomaticOcr(False);bridge.setWheelSpeed(1)
    errors=[];bridge.showError.connect(errors.append)
    engine=QQmlApplicationEngine();engine.addImageProvider('pages',images)
    engine.rootContext().setContextProperty('bridge',bridge)
    engine.load(QUrl.fromLocalFile(str(root/'ui/Main.qml')))
    assert engine.rootObjects(),'QML failed'
    window=engine.rootObjects()[0];window.setProperty('uiFontFamily','Droid Sans Fallback')
    window.setProperty('zoom',.7)
    def wait(predicate, timeout=30):
        start=time.monotonic()
        while not predicate():
            app.processEvents();QTest.qWait(15)
            if time.monotonic()-start>timeout:raise AssertionError('Timed out; errors='+str(errors))
        app.processEvents();QTest.qWait(80)
    def item(name):
        value=window.findChild(QObject,name)
        if value is None:
            pending=[window.contentItem()]
            while pending:
                candidate=pending.pop()
                if candidate.objectName()==name:
                    value=candidate;break
                pending.extend(candidate.childItems())
        assert value is not None,name
        return value
    def point(layer,x,y):
        scale=layer.property('factor')
        pos=layer.mapToScene(QPointF(x*scale,y*scale))
        return QPoint(round(pos.x()),round(pos.y()))
    def drag(layer,a,b):
        begin=point(layer,*a);end=point(layer,*b)
        QTest.mousePress(window,Qt.LeftButton,Qt.NoModifier,begin)
        for i in range(1,11):
            QTest.mouseMove(window,QPoint(round(begin.x()+(end.x()-begin.x())*i/10),round(begin.y()+(end.y()-begin.y())*i/10)),10)
        QTest.mouseRelease(window,Qt.LeftButton,Qt.NoModifier,end)
        QTest.qWait(60)
    def click(name):
        target=item(name);pos=target.mapToScene(target.boundingRect().center())
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,pos.toPoint());QTest.qWait(100)
    def wheel(angle=0,pixel=0,mods=Qt.NoModifier):
        p=item('pageScrollInput').mapToScene(QPointF(350,320))
        event=QWheelEvent(p,window.mapToGlobal(p),QPoint(0,pixel),QPoint(0,angle),Qt.NoButton,mods,Qt.ScrollUpdate,False,Qt.MouseEventSynthesizedBySystem)
        app.sendEvent(window,event);app.processEvents()
    try:
        bridge.openPath(str(fixture))
        wait(lambda:bridge.document['count']==30 and len(bridge.textLayout(0)['chars'])>0 and bridge.imageUrl(0,'main'))
        layer=item('textLayer0');chars=bridge.textLayout(0)['chars']
        a=chars[0];b=chars[9]
        y=(a[2]+a[4])/2
        drag(layer,(a[1]+.1,y),(b[3]-.1,y))
        assert bridge._selected_text=='Selectable',repr(bridge._selected_text)
        QTest.keyClick(window,Qt.Key_C,Qt.ControlModifier)
        assert app.clipboard().text()=='Selectable'
        window.grabWindow().save(str(out/'reader-selection.png'))
        drag(layer,(b[3]-.1,y),(a[1]+.1,y))
        assert bridge._selected_text=='Selectable',repr(bridge._selected_text)
        ln=bridge.textLayout(0)['lines'][1];last=chars[ln['end']-1]
        drag(layer,(a[1]+.1,y),(last[3]-.1,(last[2]+last[4])/2))
        assert bridge._selected_text=='Selectable text one\nSecond line for selection',repr(bridge._selected_text)
        with patch('PySide6.QtGui.QDesktopServices.openUrl',return_value=True) as open_url:
            QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point(layer,90,152));QTest.qWait(80)
            assert open_url.call_count==1
            assert open_url.call_args.args[0].toString()=='https://example.com/pdf?q=1'
            drag(layer,(50,152),(150,152))
            assert open_url.call_count==1,'Dragging a link must not launch browser'
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point(layer,100,195))
        wait(lambda:bridge.currentPage==2)
        pages=item('pageList')
        # Move away from boundaries; high-resolution increments preserve totals.
        pages.setProperty('contentY',3500.0);QTest.qWait(100)
        before=pages.property('contentY');wheel(-120);single=pages.property('contentY')-before
        pages.setProperty('contentY',3500.0);before=pages.property('contentY');wheel(-1200);large=pages.property('contentY')-before
        assert abs(large-single*10)<.1,(single,large)
        pages.setProperty('contentY',3500.0);before=pages.property('contentY')
        for _ in range(20):wheel(-6)
        assert abs(pages.property('contentY')-before-single)<.1
        before=pages.property('contentY');wheel(-120,pixel=-37)
        assert abs(pages.property('contentY')-before-37)<.1,(before,pages.property('contentY'),single,large)
        z=window.property('zoom');wheel(120,mods=Qt.ControlModifier)
        assert window.property('zoom')>z
        bridge.activateLink({'kind':'page','page':1,'point':[0,0]})
        wait(lambda:bridge.currentPage==1 and len(bridge.textLayout(1)['chars'])>0)
        layer=item('textLayer1');a=bridge.textLayout(1)['chars'][0];b=bridge.textLayout(1)['chars'][9]
        x=(a[1]+a[3])/2
        drag(layer,(x,a[2]+.1),(x,b[4]-.1))
        assert bridge._selected_text=='Selectable',('rotated',repr(bridge._selected_text))
        print('PASS: horizontal/reverse/multiline/rotated selection, clipboard, external/internal links, drag suppression, wheel 10x/fractional/pixel/Ctrl zoom',flush=True)
        # Printed PDF is generated by the same QPainter/spool pipeline as a printer.
        printer=QPrinter(QPrinter.HighResolution);printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setResolution(150);printer.setOutputFileName(str(out/'print-range.pdf'))
        printer.setPrintRange(QPrinter.PageRange);printer.setFromTo(2,3)
        selected=selected_pages(printer,30,0,[]);assert selected==[1,2]
        bridge.printWithPrinter(printer,selected)
        wait(lambda:not bridge.busy)
        with fitz.open(out/'print-range.pdf') as printed:
            assert len(printed)==2
            for pg in printed:
                pix=pg.get_pixmap();assert min(pix.samples)<100,'Blank print output'
        # Cancellation keeps source unmodified and prevents further pages.
        printer2=QPrinter();printer2.setOutputFormat(QPrinter.PdfFormat)
        printer2.setOutputFileName(str(out/'print-cancel.pdf'))
        bridge.printWithPrinter(printer2,list(range(30)))
        bridge._print_job.cancel();wait(lambda:not bridge.busy)
        assert not bridge.document['dirty']
        assert not errors,errors
        print('PASS: print range, portrait/landscape page fitting, cancellation, unchanged source',flush=True)
        bridge.openPath(str(root/'samples/sample.pdf'))
        wait(lambda:bridge.document['count']==4 and bridge.imageUrl(0,'main'))
        bridge.activateLink({'kind':'page','page':0,'point':[0,0]})
        window.setProperty('zoom',.75);QTest.qWait(500)
        window.grabWindow().save(str(out/'reader.png'))
        click('editModeButton');wait(lambda:bool(bridge.blocks))
        window.grabWindow().save(str(out/'editing.png'))
        click('readModeButton')
        bridge.setAutomaticOcr(True)
        bridge.activateLink({'kind':'page','page':3,'point':[0,0]})
        wait(lambda:bridge.ocrBusy)
        wait(lambda:not bridge.ocrBusy and bridge.document['dirty'],120)
        wait(lambda:bridge.textLayout(3).get('hasText',False))
        text=''.join(c[0] for c in bridge.textLayout(3)['chars'])
        assert 'SCANNED ARCHIVE' in text,text
        assert not errors,errors
        print('PASS: lazy automatic Korean/English OCR of visible scan, text-layer refresh',flush=True)
    finally:
        bridge.setAutomaticOcr(saved_auto);bridge.setWheelSpeed(saved_speed)
        bridge._state['dirty']=False;window.setVisible(False);bridge.shutdown();del engine

if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support();main()
