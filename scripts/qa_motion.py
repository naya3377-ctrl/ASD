"""Interface motion on the real window: timing, interruption and work it must not cause.

Checks, with the bundled font and a real document:
- a toolbar button shrinks its content on press (1 → .97) and runs its command at once;
- a menu fades in, and a closing menu takes no input while a click outside still lands;
- the comment and side panels take their width in one step, fade their content,
  survive rapid toggling, a tab switch and Ctrl+S mid-transition, and end in the right state;
- opening and closing panels asks for no more page renders with motion than without;
- 동작 줄이기 makes the same changes at once, and switching it mid-transition is safe;
- an open body-text edit keeps its text and cursor through panel, theme and motion changes.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen'); os.environ.setdefault('QT_QUICK_BACKEND', 'software')
from pathlib import Path
import sys, time
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))


def main():
    import fitz
    from PySide6.QtCore import QUrl, QObject, Qt, QByteArray, qInstallMessageHandler
    from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QInputMethodEvent
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from bichaek.bridge import Images
    from bichaek.tabs import Documents
    from bichaek.typefaces import install
    out = root / 'test-output'; out.mkdir(exist_ok=True)
    sources = []
    for name in ('Motion A.pdf', 'Motion B.pdf'):
        path = out / name
        with fitz.open() as pdf:
            for index in range(3):
                page = pdf.new_page(width=595, height=842); page.insert_font(fontname='K', fontbuffer=fitz.Font('korea').buffer)
                for line in range(10):
                    page.insert_text((72, 120 + line * 40), f'전시 서문 {index + 1}-{line + 1} 문단입니다', fontname='K', fontsize=14)
            pdf.subset_fonts(); pdf.save(path)
        sources.append(path)
    QQuickStyle.setStyle('Basic'); app = QApplication([])
    install(root / 'assets' / 'fonts'); app.setFont(QFont('Pretendard', 10))
    QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font('korea').buffer))
    warnings = []
    qInstallMessageHandler(lambda k, c, m: warnings.append(m) if ('file:' in m or 'Error' in m) else None)
    images = Images(); documents = Documents(images); b = documents.activeBridge
    saved = (b.automaticOcr, b.reduceMotion, b.themeMode)
    b.setAutomaticOcr(False); b.setReduceMotion(False); b.setThemeMode('light')
    engine = QQmlApplicationEngine(); engine.addImageProvider('pages', images)
    engine.addImageProvider('icon', __import__('bichaek.icons', fromlist=['Icons']).Icons(root / 'assets' / 'icons'))
    ctx = engine.rootContext(); ctx.setContextProperty('bridge', b); ctx.setContextProperty('documents', documents); ctx.setContextProperty('iconTint', True)
    engine.load(QUrl.fromLocalFile(str(root / 'ui/Main.qml'))); assert engine.rootObjects(), warnings
    w = engine.rootObjects()[0]; w.setProperty('width', 1320); w.setProperty('height', 900)
    renders = []

    def wait(pred, timeout=30):
        start = time.monotonic()
        while not pred():
            app.processEvents(); QTest.qWait(10)
            assert time.monotonic() - start < timeout, ('timeout', warnings[-6:])

    def item(name):
        pending = [w.contentItem()]
        while pending:
            obj = pending.pop()
            if obj.objectName() == name: return obj
            pending.extend(obj.childItems())
        found = w.findChild(QObject, name); assert found is not None, name
        return found

    def centre(obj): return obj.mapToScene(obj.boundingRect().center()).toPoint()
    def click(name): QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, centre(item(name))); app.processEvents()
    def holder(panel): return panel.childItems()[0]
    def settled(panel, open_):
        return panel.property('visible') == open_ and (not open_ or abs(holder(panel).property('opacity') - 1) < 1e-6)

    try:
        documents.openPaths([str(p) for p in sources]); wait(lambda: documents.tabModel.rowCount() == 2)
        c = documents.activeBridge; wait(lambda: c.document.get('count') == 3 and c.imageUrl(0, 'main') and not w.property('restoring'))
        for bridge in (documents.activeBridge,): bridge.pageImageChanged.connect(lambda page, kind: renders.append((page, kind)))
        QTest.qWait(300)

        # 1. Press feedback on content only, command at once.
        button = item('settingsButton')
        QTest.mousePress(w, Qt.LeftButton, Qt.NoModifier, centre(button)); QTest.qWait(45)
        assert button.property('press') < .995, ('no press feedback', button.property('press'))
        assert abs(button.property('width') - 32) < 1e-6, 'click area changed on press'
        QTest.mouseRelease(w, Qt.LeftButton, Qt.NoModifier, centre(button)); QTest.qWait(30)
        assert item('settingsDialog').property('visible'), 'command did not run on click'
        QTest.qWait(200); assert abs(button.property('press') - 1) < 1e-6
        item('settingsDialog').close(); QTest.qWait(50)

        # 2. Menus: fade in; while closing, no input on the menu, clicks outside land.
        menu = item('moreMenu')
        click('moreButton'); QTest.qWait(40)
        assert 0 < menu.property('opacity') < 1, ('menu did not fade in', menu.property('opacity'))
        QTest.qWait(250); assert abs(menu.property('opacity') - 1) < 1e-6 and menu.property('accepting')
        sidebar_before = w.property('sidebarOpen')
        menu.close(); assert not menu.property('accepting'), 'closing menu still accepts input'
        QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, centre(item('sidebarButton')))
        app.processEvents(); assert w.property('sidebarOpen') != sidebar_before, 'click during menu fade-out was lost'
        wait(lambda: not menu.property('visible'), timeout=2)
        w.setProperty('sidebarOpen', True); QTest.qWait(300)

        # 3. Panels: width in one step, content fades; close gives the width back once.
        dock = item('commentsDock'); workspace_widths = []
        pages = item('pageList'); pages.widthChanged.connect(lambda: workspace_widths.append(pages.property('width')))
        renders.clear(); click('commentsModeButton'); app.processEvents()
        assert dock.property('visible'), 'panel width not taken at once'
        QTest.qWait(60); mid = holder(dock).property('opacity'); assert 0 < mid < 1, ('panel content did not fade', mid)
        wait(lambda: settled(dock, True), timeout=2); QTest.qWait(400)
        assert len(set(workspace_widths)) == 1, ('page area resized more than once on open', workspace_widths)
        opened = len(renders)
        workspace_widths.clear(); click('readModeButton'); app.processEvents()
        assert dock.property('visible') and not w.property('commentsOpen'), 'state must change at once; the width later'
        wait(lambda: settled(dock, False), timeout=2); QTest.qWait(400)
        assert len(set(workspace_widths)) == 1, ('page area resized more than once on close', workspace_widths)
        motion_renders = len(renders)

        # 4. The same round trip with 동작 줄이기: immediate, and no fewer renders than with motion.
        c.setReduceMotion(True); app.processEvents(); renders.clear()
        click('commentsModeButton'); app.processEvents(); assert settled(dock, True), 'reduce motion: panel not immediate'
        QTest.qWait(400); click('readModeButton'); app.processEvents(); assert settled(dock, False), 'reduce motion: close not immediate'
        QTest.qWait(400); reduced_renders = len(renders)
        assert motion_renders <= reduced_renders + 1, ('motion caused extra renders', motion_renders, reduced_renders)
        QTest.mousePress(w, Qt.LeftButton, Qt.NoModifier, centre(button)); QTest.qWait(30)
        assert abs(button.property('press') - 1) < 1e-6, 'reduce motion: button still scales'
        QTest.mouseRelease(w, Qt.LeftButton, Qt.NoModifier, centre(button)); QTest.qWait(30); item('settingsDialog').close()
        c.setReduceMotion(False); app.processEvents()

        # 5. Rapid toggling, and 동작 줄이기 switched mid-transition.
        for i in range(12):
            w.setProperty('sidebarOpen', not w.property('sidebarOpen')); QTest.qWait(17)
        sidebar = item('sidebarPanel'); final = w.property('sidebarOpen')
        wait(lambda: settled(sidebar, final), timeout=2)
        w.setProperty('commentsOpen', True); QTest.qWait(50); c.setReduceMotion(True); QTest.qWait(20)
        w.setProperty('commentsOpen', False); app.processEvents(); assert settled(dock, False), 'reduce motion mid-transition'
        c.setReduceMotion(False); w.setProperty('sidebarOpen', True); QTest.qWait(300)

        # 6. A tab switch and Ctrl+S during a panel transition.
        c.rotateSelected(); wait(lambda: c.document.get('dirty') and not c.busy)
        click('commentsModeButton'); QTest.qWait(40)
        QTest.keyClick(w, Qt.Key_S, Qt.ControlModifier); wait(lambda: not c.document.get('dirty') and not c.busy, timeout=20)
        documents.cycle(1); wait(lambda: documents.activeBridge is not c and not w.property('restoring'))
        QTest.qWait(40); documents.cycle(-1); wait(lambda: documents.activeBridge is c and not w.property('restoring'))
        wait(lambda: settled(dock, bool(w.property('commentsOpen'))), timeout=3)
        assert w.property('commentsOpen') and w.property('workspaceMode') == 'comments', 'panel state lost across tab switch'
        click('readModeButton'); wait(lambda: settled(dock, False), timeout=2)

        # 7. An open body-text edit keeps its text and cursor through panel, theme and motion changes.
        click('editModeButton'); wait(lambda: c.blocksAt(0))
        block = max(c.blocksAt(0), key=lambda x: len(x['text'])); c.editBlock(block)
        wait(lambda: c.liveEditor.ready and not c.liveEditor.loading)
        field = item('replacementText'); field.forceActiveFocus(); QTest.keyClick(w, Qt.Key_End, Qt.ControlModifier)
        for ch in ' 추가':
            event = QInputMethodEvent(); event.setCommitString(ch); QGuiApplication.sendEvent(w.focusObject(), event); QTest.qWait(12)
        wait(lambda: c.liveEditor.doc.toPlainText().endswith(' 추가'))
        text, cursor = c.liveEditor.doc.toPlainText(), field.property('cursorPosition')
        for change in (lambda: w.setProperty('sidebarOpen', False), lambda: c.setThemeMode('dark'), lambda: c.setReduceMotion(True),
                       lambda: w.setProperty('sidebarOpen', True), lambda: c.setThemeMode('light'), lambda: c.setReduceMotion(False)):
            change(); QTest.qWait(90)
            assert item('textEditorSession').property('visible'), 'edit closed by an interface change'
            assert c.liveEditor.doc.toPlainText() == text and field.property('cursorPosition') == cursor, 'edit text or cursor moved'
        click('cancelTextButton'); wait(lambda: not item('textEditorSession').property('visible'))

        assert not warnings, warnings
        print(f'PASS: press feedback without moving the click area; menu fade in, no input while closing; panels resize once '
              f'and fade ({motion_renders} vs {reduced_renders} renders with/without motion); rapid toggles, tab switch, '
              f'Ctrl+S and 동작 줄이기 mid-transition settle correctly; an open edit keeps its text and cursor', flush=True)
    finally:
        active = documents.activeBridge
        active.setAutomaticOcr(saved[0]); active.setReduceMotion(saved[1]); active.setThemeMode(saved[2])
        w.setVisible(False); documents.shutdown(); del engine; qInstallMessageHandler(None)


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support(); main()
