"""Screens of the Preview-style amekaji design, in light and dark, with the bundled font.

Saves test-output/design-*.png for review and fails on QML warnings.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QT_QUICK_BACKEND','software')
from pathlib import Path
import sys,time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))


class FakeLibrary:
    """Recent documents for the start screen without touching real settings."""
    def __init__(self, paths):
        from PySide6.QtCore import QObject, Property, Signal, Slot
        class Library(QObject):
            changed = Signal()
            def __init__(self, rows): super().__init__(); self.rows = rows
            @Property(bool, notify=changed)
            def enabled(self): return True
            @Property('QVariantList', notify=changed)
            def recent(self): return self.rows
            @Slot()
            def clear(self): pass
            @Slot(str)
            def forget(self, path): pass
            @Slot(bool)
            def setEnabled(self, value): pass
        self.object = Library([{'name': Path(p).name, 'path': str(p), 'exists': True, 'page': i*3} for i, p in enumerate(paths)])


def main():
    import fitz
    from PySide6.QtCore import QUrl,QObject,Qt,QPointF,qInstallMessageHandler
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from bichaek.bridge import Images
    from bichaek.tabs import Documents
    from bichaek.typefaces import install
    root=Path(__file__).resolve().parent.parent;out=root/'test-output';out.mkdir(exist_ok=True)
    report=out/'디자인 검토 보고서.pdf'
    with fitz.open() as doc:
        for index in range(6):
            p=doc.new_page(width=595,height=842)
            p.insert_text((72,110),'『문화예술활동현황조사』' if index==0 else f'{index}. 조사 개요',fontname='korea',fontsize=24 if index==0 else 18)
            for line in range(12):p.insert_text((72,170+line*26),f'문화예술 활동 건수와 분야별 현황을 정리했습니다 {line+1}',fontname='korea',fontsize=12)
        first=doc[0]
        a=first.add_highlight_annot(first.search_for('문화예술 활동 건수와 분야별 현황을 정리했습니다 1')[0])
        a.set_info(content='도입부 문장은 전시 서문과 톤을 맞춰 주세요.',title='큐레이터');a.update()
        n=first.add_text_annot((420,300),'도판 번호 확인 필요');n.set_info(title='편집자');n.update()
        doc.save(report)
    QQuickStyle.setStyle('Basic');app=QApplication([])
    families=install(root/'assets'/'fonts')
    from PySide6.QtGui import QFont
    app.setFont(QFont('Pretendard',10))   # as bichaek/app.py does
    assert 'Pretendard' in families,families
    warnings=[]
    qInstallMessageHandler(lambda k,c,m: warnings.append(m) if ('file:' in m or 'Error' in m) else None)
    images=Images();documents=Documents(images);b=documents.activeBridge
    saved=(b.automaticOcr,b.annotationAuthor,b.themeMode)
    b.setAutomaticOcr(False);b.setAnnotationAuthor('큐레이터')
    library=FakeLibrary([report,out/'전시 도록 초안.pdf',out/'작가론 원고.pdf'])
    engine=QQmlApplicationEngine();engine.addImageProvider('pages',images)
    engine.addImageProvider('icon',__import__('bichaek.icons',fromlist=['Icons']).Icons(root/'assets'/'icons'))
    ctx=engine.rootContext()
    ctx.setContextProperty('bridge',b);ctx.setContextProperty('documents',documents)
    ctx.setContextProperty('library',library.object);ctx.setContextProperty('iconTint',True)
    engine.load(QUrl.fromLocalFile(str(root/'ui/Main.qml')))
    assert engine.rootObjects(),warnings
    w=engine.rootObjects()[0];w.setProperty('width',1440);w.setProperty('height',900)
    def wait(predicate,timeout=30):
        started=time.monotonic()
        while not predicate():
            app.processEvents();QTest.qWait(20)
            if time.monotonic()-started>timeout:raise AssertionError(('timeout',warnings[-6:]))
        app.processEvents();QTest.qWait(120)
    def item(name):
        x=w.findChild(QObject,name)
        if x:return x
        todo=[w.contentItem()]
        while todo:
            x=todo.pop()
            if x.objectName()==name:return x
            todo.extend(x.childItems())
        raise AssertionError(name)
    def click(name):
        x=item(name);pos=x.mapToScene(x.boundingRect().center())
        QTest.mouseClick(w,Qt.LeftButton,Qt.NoModifier,pos.toPoint());QTest.qWait(120)
    def shot(name):
        app.processEvents();QTest.qWait(250);w.grabWindow().save(str(out/f'design-{name}.png'))
    try:
        for theme in ('light','dark'):
            documents.activeBridge.setThemeMode(theme);QTest.qWait(100)
            if theme=='light':
                # The character waves hello on its own, settles, and waves again when clicked.
                hello=item('startCharacter')
                wait(lambda:not hello.property('playing'),timeout=10)
                assert hello.property('armAngle')==0 and hello.property('hop')==0,'character did not settle'
                shot('start')
                click('startCharacter');assert hello.property('playing'),'click did not wave'
                QTest.qWait(700);shot('start-wave')
                wait(lambda:not hello.property('playing'),timeout=10)
            if not documents.activeBridge.document.get('count'):
                documents.openPaths([str(report)]);c=documents.activeBridge
                wait(lambda:c.document.get('count')==6 and c.imageUrl(0,'main') and c.textLayout(0)['chars'])
            c=documents.activeBridge;c.setAutomaticOcr(False)
            w.setProperty('workspaceMode','read');w.setProperty('commentsOpen',False);w.setProperty('tool','read');QTest.qWait(200)
            shot(f'reader-{theme}')
            click('commentsModeButton');wait(lambda:not c.annotationsLoading and len(c.annotations)==2)
            chars=c.textLayout(0)['chars'];c.selectCharacters(0,0,12)
            c.selectAnnotation(0,c.annotations[0]['id'])
            shot(f'comments-{theme}')
            c.composeSelectionComment();wait(lambda:item('annotationEditor').property('visible'))
            item('commentBody').setProperty('text','제목의 겹낫표는 도록 표기와 같게 유지')
            shot(f'draft-{theme}')
            click('cancelComment');wait(lambda:not item('annotationEditor').property('visible'))
            click('editModeButton');QTest.qWait(300)
            shot(f'edit-{theme}')
        documents.activeBridge.setThemeMode('light');QTest.qWait(100)
        click('readModeButton')
        item('settingsDialog').open();shot('settings');item('settingsDialog').close()
        c=documents.activeBridge;c.showError.emit('PDF 내부 구조의 일부를 읽지 못해서 작업을 마치지 못했어요. (MuPDF: code=8: invalid key in dict)')
        QTest.qWait(200);shot('error')
        for d in w.findChildren(QObject):
            if d.metaObject().className().startswith('AppDialog') and d.property('visible'):d.close()
        QTest.qWait(150)
        c.showMerge();QTest.qWait(300);shot('merge');item('mergeDialog').close();QTest.qWait(150)
        from PySide6.QtCore import QMetaObject
        QMetaObject.invokeMethod(item('aboutDialog'),'open')
        QTest.qWait(400);shot('about')
        assert item('aboutCharacter').property('visible')
        assert not warnings,warnings
        print('PASS: design screens saved to test-output/design-*.png; the start character waves and settles; bundled fonts loaded; no QML warnings',flush=True)
    finally:
        active=documents.activeBridge;active.setAutomaticOcr(saved[0]);active.setAnnotationAuthor(saved[1]);active.setThemeMode(saved[2])
        w.setVisible(False);documents.shutdown();del engine;qInstallMessageHandler(None)

if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support();main()
