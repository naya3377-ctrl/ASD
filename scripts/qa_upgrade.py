"""UI regression: preview reuse, mixed geometry, multi-file merge and live edits.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
from pathlib import Path
import sys,time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))


def main():
    import fitz
    from PySide6.QtCore import QUrl,QObject,Qt,QByteArray
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from bichaek.bridge import Images,Bridge
    root=Path(__file__).resolve().parent.parent;out=root/'test-output';out.mkdir(exist_ok=True)
    QQuickStyle.setStyle('Basic');app=QApplication([])
    QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font('korea').buffer))
    images=Images();bridge=Bridge(images);saved_auto=bridge.automaticOcr;bridge.setAutomaticOcr(False)
    errors=[];bridge.showError.connect(errors.append)
    engine=QQmlApplicationEngine();engine.addImageProvider('pages',images)
    engine.rootContext().setContextProperty('bridge',bridge);engine.load(QUrl.fromLocalFile(str(root/'ui/Main.qml')))
    assert engine.rootObjects();window=engine.rootObjects()[0];window.setProperty('uiFontFamily','Droid Sans Fallback')
    window.setProperty('zoom',.62)
    def wait(predicate,timeout=30):
        began=time.monotonic()
        while not predicate():
            app.processEvents();QTest.qWait(20)
            if time.monotonic()-began>timeout:raise AssertionError(str(errors))
        app.processEvents();QTest.qWait(100)
    def item(name):
        value=window.findChild(QObject,name)
        if value:return value
        todo=[window.contentItem()]
        while todo:
            child=todo.pop()
            if child.objectName()==name:return child
            todo.extend(child.childItems())
        raise AssertionError(name)
    try:
        bridge.openPath(str(root/'samples/sample.pdf'))
        wait(lambda:bridge.document['count']==4 and all(bridge.imageUrl(x,'thumb') for x in range(3)))
        paper=item('thumbnailPaper2')
        assert abs(paper.width()/paper.height()-842/595)<.01,'Landscape thumbnail was distorted'
        wait(lambda:not bridge._pending_images)
        bridge.requestPage(0,'main',1280)
        wait(lambda:bridge._sources.get((0,'main'),'').endswith('-1280') and not bridge._pending_images)
        correct=bridge._sources[(0,'main')]
        bridge.requestPage(0,'main',512)
        wait(lambda:bridge._sources.get((0,'main'),'').endswith('-512') and not bridge._pending_images)
        dead=bridge._sources[(0,'main')]
        with images.lock:images.bytes-=images.images.pop(dead).sizeInBytes()
        assert bridge.imageUrl(0,'main')==''
        bridge.requestPage(0,'main',1280)
        assert bridge._sources[(0,'main')]==correct and bridge.imageUrl(0,'main')
        assert not bridge._pending_images,'Cached preview should reconnect without rendering'
        bridge.setCacheMiB(1024);assert images.budget==1024*1024*1024
        bridge.setCacheMiB(512)
        assert any(x is not None for x in bridge.frames.frames),'Shared frames not used'
        window.grabWindow().save(str(out/'reader-030.png'))
        print('PASS: landscape previews, cache-hit reconnect after eviction, shared frame delivery, cache settings',flush=True)
        # Add two real files through the same preflight pipeline as the picker.
        bridge.showMerge();QTest.qWait(200)
        assert item('mergeDialog').property('visible')
        bridge.addMergePaths([QUrl.fromLocalFile(str(root/'samples/sample.pdf')),str(root/'samples/sample.pdf')])
        wait(lambda:len(bridge.mergeItems)==2 and not bridge.mergeInspecting)
        first_id=bridge.mergeItems[0]['id'];bridge.moveMergeItem(0,1)
        assert bridge.mergeItems[1]['id']==first_id
        QTest.qWait(200);window.grabWindow().save(str(out/'merge-030.png'))
        target=out/'combined-ui.pdf';original=(root/'samples/sample.pdf').read_bytes()
        bridge.startMergeTo(str(target));wait(lambda:bool(bridge.mergeResult) and not bridge.mergeBusy,60)
        with fitz.open(target) as doc:
            assert len(doc)==8 and 'A document' in doc[4].get_text()
            assert doc.get_toc()[0][2]==1
        assert (root/'samples/sample.pdf').read_bytes()==original
        assert bridge.document['count']==4 and not bridge.document['dirty']
        bridge.removeMergeItem(1);bridge.removeMergeItem(0)
        bridge.edit('add_text',{'page':0,'rect':[45,300,450,345],'text':'UNSAVED LIVE EDIT','size':14})
        wait(lambda:not bridge.busy and bridge.document['dirty'])
        bridge.addCurrentToMerge();bridge.addMergePaths([str(root/'samples/sample.pdf')])
        wait(lambda:len(bridge.mergeItems)==2 and not bridge.mergeInspecting)
        target2=out/'combined-live.pdf';bridge.startMergeTo(str(target2));wait(lambda:not bridge.mergeBusy and bridge.mergeResult==str(target2),60)
        with fitz.open(target2) as doc:
            assert 'UNSAVED LIVE EDIT' in doc[0].get_text()
            assert 'UNSAVED LIVE EDIT' not in doc[4].get_text()
        assert bridge.document['dirty'] and (root/'samples/sample.pdf').read_bytes()==original
        assert not errors,errors
        print('PASS: merge dialog, inspect, reorder, 8-page output, unsaved current document snapshot, unchanged originals',flush=True)
    finally:
        bridge.setAutomaticOcr(saved_auto);bridge._state['dirty']=False
        window.setVisible(False);bridge.shutdown();del engine

if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support();main()
