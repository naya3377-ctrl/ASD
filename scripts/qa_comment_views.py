"""The comment panel's two views, driven as a reader does, on PDFs that used to fail.

On a report with a damaged unused object, a PDF that allows comments but not
copying, and a turned page:
- a highlight goes to the 형광펜 view (not the memo list) and the panel follows it;
- a memo on dragged words and a memo on a place go to the 메모 view;
- editing a memo shows the memo only: no marked passage, no colour choice,
  and the mark's colour, passage and position stay exactly as they were;
- a memo added from the 형광펜 view, a recolour that keeps the memo, a reply;
- a mark clicked on the page opens the view that holds it;
- 모두 복사 puts every passage and memo on the clipboard in page order,
  and leaks no text from a PDF that forbids copying;
- delete and undo, save, and an independent reopen that finds everything;
then 60 marks over several pages: counts, order and view switching stay right.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen'); os.environ.setdefault('QT_QUICK_BACKEND', 'software')
from pathlib import Path
import sys, time
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root)); sys.path.insert(0, str(root / 'scripts'))


def main():
    import fitz
    from unittest.mock import patch
    from PySide6.QtCore import QUrl, QObject, Qt, QByteArray, QPointF, QMetaObject, Q_ARG, qInstallMessageHandler
    from PySide6.QtGui import QFontDatabase, QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtTest import QTest
    from bichaek.bridge import Images
    from bichaek.tabs import Documents
    from qa_comment_flows import build, TITLE
    out = root / 'test-output' / 'comment-views'; out.mkdir(parents=True, exist_ok=True)
    paths = build(out)
    many = out / '형광펜 60개.pdf'
    with fitz.open() as doc:
        for index in range(6):
            p = doc.new_page(width=595, height=842)
            for line in range(10): p.insert_text((72, 100 + line * 40), f'{index + 1}쪽 {line + 1}번째 문장입니다', fontname='korea', fontsize=14)
        doc.save(many)
    QQuickStyle.setStyle('Basic'); app = QApplication([])
    QFontDatabase.addApplicationFontFromData(QByteArray(fitz.Font('korea').buffer))
    warnings = []
    qInstallMessageHandler(lambda k, c, m: warnings.append(m) if ('file:' in m or 'ReferenceError' in m or 'TypeError' in m) else None)
    images = Images(); documents = Documents(images); b = documents.activeBridge
    saved = (b.automaticOcr, b.annotationAuthor, b.annotationColor)
    b.setAutomaticOcr(False); b.setAnnotationAuthor('큐레이터'); b.setAnnotationColor('#ffd54f')
    errors = []; documents.showError.connect(errors.append)
    engine = QQmlApplicationEngine(); engine.addImageProvider('pages', images)
    engine.rootContext().setContextProperty('bridge', b); engine.rootContext().setContextProperty('documents', documents)
    engine.load(QUrl.fromLocalFile(str(root / 'ui/Main.qml'))); assert engine.rootObjects(), warnings
    window = engine.rootObjects()[0]; window.setProperty('uiFontFamily', 'Droid Sans Fallback')
    window.setProperty('width', 1500); window.setProperty('height', 940)

    def wait(predicate, timeout=30):
        started = time.monotonic()
        while not predicate():
            app.processEvents(); QTest.qWait(20)
            if time.monotonic() - started > timeout: raise AssertionError(('timeout', errors, warnings[-8:]))
        app.processEvents(); QTest.qWait(80)

    def item(name, required=True):
        pending = [window.contentItem()]
        while pending:
            x = pending.pop()
            if x.objectName() == name: return x
            pending.extend(x.childItems())
        x = window.findChild(QObject, name)
        if x is None and required: raise AssertionError(name)
        return x

    def click(name):
        x = item(name) if isinstance(name, str) else name
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, x.mapToScene(x.boundingRect().center()).toPoint()); QTest.qWait(100)

    def inside(parent, name):
        """The named item within one row (every row has its own colour dots)."""
        pending = [item(parent)]
        while pending:
            x = pending.pop()
            if x.objectName() == name and x.isVisible(): return x
            pending.extend(x.childItems())
        raise AssertionError((parent, name))

    def span(c, text, page=0):
        chars = c.textLayout(page)['chars']; joined = ''.join(ch[0] for ch in chars)
        start = joined.index(text) if text in joined else 0
        return chars[start:start + len(text)]

    def drag(c, text, page=0):
        layer = item('textLayer%d' % page); f = layer.property('factor'); chosen = span(c, text, page)
        a = layer.mapToScene(QPointF(chosen[0][1] * f + 1, (chosen[0][2] + chosen[0][4]) / 2 * f))
        z = layer.mapToScene(QPointF(chosen[-1][3] * f - 1, (chosen[-1][2] + chosen[-1][4]) / 2 * f))
        QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, a.toPoint())
        for i in range(1, 9): QTest.mouseMove(window, (a + (z - a) * (i / 8)).toPoint(), 12)
        QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, z.toPoint()); QTest.qWait(80)
        wait(lambda: c.textSelection['count'] >= len(text) - 1)

    def panel(): return item('commentsPanel')
    def view(): return panel().property('view')
    def form_open(): return item('annotationEditor').property('visible')

    def write(text):
        wait(form_open)
        item('commentBody').setProperty('text', text); click('applyComment')
        wait(lambda: not documents.activeBridge.busy and not form_open())

    def show(kind, index):
        """Scroll the list to an entry and return its row."""
        QMetaObject.invokeMethod(item('commentsList'), 'positionViewAtIndex', Q_ARG(int, index), Q_ARG(int, 1))
        wait(lambda: item(kind + str(index), required=False) is not None)
        return kind + str(index)

    def index_of(rows, ident): return next(i for i, a in enumerate(rows) if a['id'] == ident)

    def flows(label, path):
        documents.openPaths([str(path)]); c = documents.activeBridge
        wait(lambda: c.document.get('name') == path.name and c.document['count'] == 4 and not c.busy)
        wait(lambda: c.imageUrl(0, 'main') and c.textLayout(0)['chars'])
        if window.property('workspaceMode') != 'comments': click('commentsModeButton')
        wait(lambda: window.property('commentsOpen') and not c.annotationsLoading)
        window.setProperty('zoom', .9); QTest.qWait(250)
        # 1. A highlight: in the 형광펜 view only, and the panel follows it there.
        panel().setProperty('view', 'notes')
        drag(c, TITLE); click('commentHighlightButton'); wait(lambda: len(c.annotationMarks) == 1 and not c.busy)
        window.setProperty('tool', 'read')
        assert c.annotationNotes == [] and view() == 'marks', (c.annotationNotes, view())
        plain = c.annotationMarks[0]
        # 2. A memo on dragged words, and a memo on a place: the 메모 view.
        drag(c, '통계정보보고서'); click('commentNoteButton'); wait(form_open)
        # A new memo shows the words it will mark (none can be read from a no-copy PDF) and a colour choice.
        assert view() == 'notes' and item('commentFormQuote').property('visible') == (label != 'nocopy') and item('commentFormColors').property('count') == 5, (view(), label)
        write('제목 표기 확인'); wait(lambda: len(c.annotationNotes) == 1 and len(c.annotationMarks) == 2)
        marked = next(a for a in c.annotationNotes if a['content'] == '제목 표기 확인')
        c.clearTextSelection(); click('commentNoteButton')
        paper = item('paper0'); QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, paper.mapToScene(QPointF(paper.width() * .75, paper.height() * .2)).toPoint())
        write('여백 메모'); wait(lambda: len(c.annotationNotes) == 2 and len(c.annotationMarks) == 2)
        assert all(a['type'] == 'Text' or a['content'] for a in c.annotationNotes)
        # 3. Editing a memo: the memo only; the mark itself does not change.
        before = next(a for a in c.annotations if a['id'] == marked['id'])
        click(show('commentCard', index_of(c.annotationNotes, marked['id']))); wait(lambda: c.selectedAnnotation.get('id') == marked['id'])
        click('editComment%d' % index_of(c.annotationNotes, marked['id'])); wait(form_open)
        assert item('commentFormTitle').property('text') == '메모 수정'
        assert not item('commentFormQuote').property('visible'), 'the marked passage came along into the memo edit'
        assert item('commentFormColors').property('count') == 0, 'colour choice came along into the memo edit'
        write('제목 표기 확인 · 도록과 같게')
        after = next(a for a in c.annotations if a['id'] == marked['id'])
        assert after['content'] == '제목 표기 확인 · 도록과 같게'
        assert (after['color'], after['quote'], after['regions'], after['type']) == (before['color'], before['quote'], before['regions'], before['type']), (before, after)
        # 4. From the 형광펜 view: a memo on the plain highlight, then a new colour that keeps it.
        click('commentsMarksTab'); wait(lambda: view() == 'marks')
        click(show('markCard', index_of(c.annotationMarks, plain['id']))); wait(lambda: c.selectedAnnotation.get('id') == plain['id'])
        click('markMemo%d' % index_of(c.annotationMarks, plain['id'])); wait(form_open)
        assert view() == 'marks' and item('commentFormTitle').property('text') == '메모 달기' and not item('commentFormQuote').property('visible')
        write('요약: 조사 제목'); wait(lambda: len(c.annotationNotes) == 3)
        assert next(m for m in c.annotationMarks if m['id'] == plain['id'])['note'] == '요약: 조사 제목'
        click(inside('markCard%d' % index_of(c.annotationMarks, plain['id']), 'markColor_8ed7ad')); wait(lambda: not c.busy and next(a for a in c.annotations if a['id'] == plain['id'])['color'] == '#8ed7ad')
        recoloured = next(a for a in c.annotations if a['id'] == plain['id'])
        assert recoloured['content'] == '요약: 조사 제목' and recoloured['author'] == plain['author'], recoloured
        # 5. A reply keeps its thread in the memo view and is counted on the passage.
        c.selectAnnotation(0, marked['id']); c.editSelectedAnnotation('reply'); write('확인했어요')
        wait(lambda: next(m for m in c.annotationMarks if m['id'] == marked['id'])['replies'] == 1)
        assert any(a['reply'] and a['content'] == '확인했어요' for a in c.annotationNotes)
        # 6. A mark clicked on the page opens the view that holds it.
        drag(c, '2023. 12.'); click('commentHighlightButton'); wait(lambda: len(c.annotationMarks) == 3 and not c.busy)
        window.setProperty('tool', 'read'); fresh = next(m for m in c.annotationMarks if not m['note'])
        click('commentsNotesTab'); wait(lambda: view() == 'notes')
        c.focusAnnotation(0, fresh['id']); wait(lambda: view() == 'marks')
        # 7. 모두 복사: every passage and memo, in page order; nothing from a no-copy PDF.
        QGuiApplication.clipboard().setText('')
        click('copyMarksButton'); wait(lambda: '형광펜 모음' in QGuiApplication.clipboard().text())
        summary = QGuiApplication.clipboard().text()
        assert summary.count('\n· ') == 3 and '요약: 조사 제목' in summary and '제목 표기 확인 · 도록과 같게' in summary, summary
        if label == 'nocopy': assert TITLE[1:5] not in summary and '통계' not in summary, summary
        # (A pointer drag over a turned page's vertical text may stop one character short.)
        else: assert TITLE[1:5] in summary and '정보보고서' in summary, summary
        # 8. Delete from the 형광펜 view, undo.
        c.selectAnnotation(0, fresh['id'])
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes): c.deleteSelectedAnnotation()
        wait(lambda: not c.busy and len(c.annotationMarks) == 2)
        c.undo(); wait(lambda: not c.busy and len(c.annotationMarks) == 3)
        # 9. Save, and read it back independently.
        c.save(False); wait(lambda: not c.busy and not c.document['dirty'])
        with fitz.open(path) as check:
            if check.needs_pass: check.authenticate('')
            annots = {a.info['content']: (a.type[1], a.colors.get('stroke')) for a in check[0].annots()}
        assert annots.get('요약: 조사 제목', (None, None))[0] == 'Highlight', annots
        assert [round(x, 2) for x in annots['요약: 조사 제목'][1]] == [round(0x8e / 255, 2), round(0xd7 / 255, 2), round(0xad / 255, 2)], annots
        assert {'제목 표기 확인 · 도록과 같게', '여백 메모', '확인했어요'} <= set(annots), annots
        assert not errors, errors
        print(f'PASS {label}: highlight → 형광펜 view, memos → 메모 view, memo edit without passage or colour '
              f'(mark unchanged), memo and recolour from 형광펜 view, reply, page mark reveals, copy summary, delete/undo, save', flush=True)

    try:
        for label in ('damaged', 'nocopy', 'rotated'): flows(label, paths[label])
        # Sixty marks over six pages: counts, order and views stay right.
        documents.openPaths([str(many)]); c = documents.activeBridge
        wait(lambda: c.document.get('name') == many.name and c.document['count'] == 6 and not c.busy)
        if window.property('workspaceMode') != 'comments': click('commentsModeButton')
        wait(lambda: window.property('commentsOpen') and not c.annotationsLoading)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            for page in range(6):
                c.requestText(page); wait(lambda: c.textLayout(page)['chars'])
                chars = c.textLayout(page)['chars']; joined = ''.join(ch[0] for ch in chars)
                for line in range(10):
                    text = f'{page + 1}쪽 {line + 1}번째 문장입니다'; start = joined.index(text)
                    # After each mark the page's text layer reloads; select once it is back.
                    wait(lambda: (c.requestText(page), len(c.textLayout(page)['chars']) == len(chars))[1])
                    c.selectCharacters(page, start, start + len(text)); wait(lambda: c.textSelection['count'] == len(text))
                    count = len(c.annotationMarks); c.annotateSelection(['highlight', 'underline', 'strikeout'][line % 3])
                    try: wait(lambda: not c.busy and len(c.annotationMarks) == count + 1, timeout=15)
                    except AssertionError: raise AssertionError(('stress', page, line, count, len(c.annotationMarks), len(c.annotations), c.property('status'), c.textSelection, [len(c.pageAnnotations(i)) for i in range(6)]))
        if window.property('workspaceMode') != 'comments': click('commentsModeButton')
        wait(lambda: not c.annotationsLoading and len(c.annotationMarks) == 60)
        marks = c.annotationMarks
        assert [m['page'] for m in marks] == sorted(m['page'] for m in marks) and c.annotationNotes == []
        assert [m['quote'].split()[1] for m in marks[:10]] == [f'{n}번째' for n in range(1, 11)], [m['quote'] for m in marks[:10]]
        for _ in range(20):
            click('commentsNotesTab'); click('commentsMarksTab')
        wait(lambda: view() == 'marks' and item('commentsList').property('count') == 60)
        QGuiApplication.clipboard().setText(''); click('copyMarksButton')
        wait(lambda: QGuiApplication.clipboard().text().count('\n· ') == 60)
        # Switching documents keeps each document's own lists.
        documents.activate(0); wait(lambda: documents.activeBridge is not c and not documents.activeBridge.annotationsLoading)
        other = documents.activeBridge; wait(lambda: len(other.annotationMarks) == 3)
        documents.activate(3); wait(lambda: documents.activeBridge is c and len(c.annotationMarks) == 60)
        c._state['dirty'] = False
        window.grabWindow().save(str(out / 'comment-views.png'))
        assert not warnings, warnings
        print('PASS: 60 marks listed in page order in the 형광펜 view only, rapid view switching, copy of all 60, '
              'tab switch keeps each document\'s lists; no QML warnings', flush=True)
    finally:
        active = documents.activeBridge
        active.setAutomaticOcr(saved[0]); active.setAnnotationAuthor(saved[1]); active.setAnnotationColor(saved[2])
        window.setVisible(False); documents.shutdown(); del engine; qInstallMessageHandler(None)


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support(); main()
