"""Qt bridge: file dialogs, process IPC, and bounded image cache.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from collections import OrderedDict
from pathlib import Path
import json
import multiprocessing as mp
import os
import queue
import shutil
import tempfile
import time
import uuid

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer, Qt, QSize, QSettings, QSaveFile, QIODevice, QByteArray
from PySide6.QtGui import QImage, QImageReader, QGuiApplication, QFontDatabase
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtWidgets import QFileDialog, QMessageBox, QInputDialog, QLineEdit

from .text_editor import TextEditor
from .worker import engine_main, ocr_main, ocr_languages
from .rendering import Images, FramePool


class Bridge(QObject):
    annotationCommitted = Signal()
    annotationsChanged = Signal()
    openComments = Signal()
    showAnnotationEditor = Signal('QVariantMap')
    stateChanged = Signal()
    imagesChanged = Signal()
    pageImageChanged = Signal(int,str)
    pageMetricsChanged = Signal(int)
    selectionChanged = Signal()
    statusChanged = Signal()
    searchChanged = Signal()
    ocrChanged = Signal()
    blocksChanged = Signal()
    textLayoutChanged = Signal()
    textSelectionChanged = Signal()
    preferencesChanged = Signal()
    mergeChanged = Signal()
    openMergeDialog = Signal()
    textCommitted = Signal()
    imageInserted = Signal()
    fontsChanged = Signal()
    showTextEditor = Signal('QVariantMap')
    showError = Signal(str)
    requestClose = Signal()
    navigateRequested = Signal(int, float, float)
    resumeRequested = Signal(int)
    outlineRequested = Signal(int, float)
    outlineChanged = Signal()

    def __init__(self, images, hub=None):
        super().__init__()
        self.images = images
        self.hub = hub
        self.document_id = uuid.uuid4().hex
        self.workspace = None
        self.active = hub is None
        self.closed = False
        self.view_state = {}
        self.frames = hub.frames if hub else FramePool()
        self._render_queue = OrderedDict()
        self._render_scheduled = False
        self._requested_widths = {}
        self._render_errors = {}
        self.ctx = hub.ctx if hub else mp.get_context("spawn")
        if hub:
            self.inbox, self.outbox, self.process = hub.inbox, hub.outbox, hub.process
        else:
            self.inbox, self.outbox = self.ctx.Queue(), self.ctx.Queue()
            self.stopping = self.ctx.Event()
            self.process = self.ctx.Process(target=engine_main, args=(self.inbox, self.outbox, self.stopping), daemon=True)
            self.process.start()
        self._state = {"count": 0, "name": "윤DF", "dirty": False, "revision": 0,
                       "session": "", "canUndo": False, "canRedo": False, "editable": False, "printable": False, "printHighQuality": False}
        self._merge_dialog_open = False
        self._merge_items = []
        self._merge_inspecting = 0
        self._merge_busy = False
        self._merge_progress = ""
        self._merge_result = ""
        self._merge_snapshot = None
        self._merge_temp = None
        self.merge_process = self.merge_events = self.merge_cancel = None
        self._print_job = None
        self._status = "PDF를 열어 시작하세요."
        self._busy = False
        self._annotation_pages = {}
        self._annotation_focus = {}
        self._annotation_panel_open = False
        self._annotation_editor_open = False
        self._presentation_active = False
        self._annotation_loading = False
        self._annotation_token = 0
        self._page = 0
        self._selection = []
        self._selection_anchor = 0
        self._image_focus = {}
        self._tick = 0
        self._blocks = []
        self._page_blocks = {}
        self._blocks_tick = 0
        self._blocks_pending = set()
        self._query = ""
        self._hits = []
        self._hit_index = -1
        self._search_waiting = None
        self._search = []
        self._search_busy = False
        self._search_token = 0
        self._ocr_busy = False
        self._ocr_progress = ""
        self.ocr_process = None
        self.ocr_dir = None
        self.ocr_events = None
        self.ocr_cancel = None
        self._ocr_snapshot = None
        self._ocr_cancel_requested = False
        self._languages = []
        self._font_path = ""
        self._font_choice = "default"
        self._original_font_available = False
        self._font_options = []
        self._text_editor_open = False
        self._editing_target = {}
        self._editor_font_family = ""
        self._font_preview_token = 0
        self._qt_font_ids = {}
        self._live_editor = TextEditor(self)
        self._selected_text = ""
        self._text_page = -1
        self._text_start = self._text_end = 0
        self._text_layouts = OrderedDict()
        self._text_pending = set()
        self._text_tick = 0
        self._auto_attempted = set()
        self._outline = []
        self._outline_token = 0
        self.preferences = QSettings("Bichaek", "BichaekPDF")
        self.images.budget = int(self.preferences.value("cacheMiB",512))*1024*1024
        self._auto_ocr = self.preferences.value("automaticOcr", True, type=bool)
        self._wheel_speed = float(self.preferences.value("wheelSpeed", 1.0))
        self.auto_timer = QTimer(self)
        self.auto_timer.setSingleShot(True)
        self.auto_timer.setInterval(900)
        self.auto_timer.timeout.connect(self.auto_recognize)
        self._sources = {}
        self._metrics = {}
        self._pending_images = set()
        self.callbacks = {}
        self.serial = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        if not hub: self.timer.start(20)

    @Property('QVariantMap', notify=stateChanged)
    def document(self): return self._state
    @Property(bool, notify=stateChanged)
    def busy(self): return self._busy
    @Property(int, notify=selectionChanged)
    def currentPage(self): return self._page
    @Property('QVariantList', notify=selectionChanged)
    def selection(self): return self._selection
    @Property(str, notify=statusChanged)
    def status(self): return self._status
    @Property(int, notify=imagesChanged)
    def imageTick(self): return self._tick
    @Property('QVariantList', notify=blocksChanged)
    def blocks(self): return self._blocks
    @Property('QVariantList', notify=searchChanged)
    def searchResults(self): return self._search
    @Property(str, notify=searchChanged)
    def searchQuery(self): return self._query
    @Property(int, notify=searchChanged)
    def searchCount(self): return len(self._hits)
    @Property(int, notify=searchChanged)
    def searchIndex(self): return self._hit_index
    @Property('QVariantMap', notify=searchChanged)
    def activeSearchHit(self):
        return self._hits[self._hit_index] if 0 <= self._hit_index < len(self._hits) else {}
    @Property(bool, notify=searchChanged)
    def searching(self): return self._search_busy
    @Property(bool, notify=ocrChanged)
    def ocrBusy(self): return self._ocr_busy
    @Property(str, notify=ocrChanged)
    def ocrProgress(self): return self._ocr_progress
    @Property('QStringList', notify=ocrChanged)
    def languages(self): return self._languages
    @Property(str, notify=stateChanged)
    def fontName(self): return next((f["label"] for f in self.fontOptions if f["key"] == self._font_choice), "원본 글꼴 유지")

    @Property(int, notify=textLayoutChanged)
    def textTick(self): return self._text_tick

    @Property(str, notify=textLayoutChanged)
    def pageTextState(self):
        data = self._text_layouts.get(self._page)
        if not data: return "loading"
        if not data.get("copyable"): return "restricted"
        return "text" if data.get("hasText") else "empty"

    @Property('QVariantMap', notify=textSelectionChanged)
    def textSelection(self):
        return {"page": self._text_page, "start": self._text_start,
                "end": self._text_end, "count": len(self._selected_text)}

    @Property(bool, notify=preferencesChanged)
    def automaticOcr(self): return self._auto_ocr

    @Property(float, notify=preferencesChanged)
    def wheelSpeed(self): return self._wheel_speed

    @Property(int, constant=True)
    def wheelScrollLines(self):
        from PySide6.QtGui import QGuiApplication
        return QGuiApplication.styleHints().wheelScrollLines()

    @Slot(bool)
    def setAutomaticOcr(self, value):
        self._auto_ocr = value
        self.preferences.setValue("automaticOcr", value)
        self.preferencesChanged.emit()
        if value: self.auto_timer.start()
        else: self.auto_timer.stop()

    @Slot(float)
    def setWheelSpeed(self, value):
        self._wheel_speed = min(5.0, max(0.5, value))
        self.preferences.setValue("wheelSpeed", self._wheel_speed)
        self.preferencesChanged.emit()

    @Slot(int, result='QVariantList')
    def movableImages(self, page):
        return self._text_layouts.get(page, {}).get("movableImages", [])

    @Slot(int, result='QVariantMap')
    def textLayout(self, page):
        return self._text_layouts.get(page, {"chars": [], "lines": [], "copyable": False})

    @Slot(int)
    def requestText(self, page):
        if not self.active or self.closed or not 0 <= page < self._state["count"]: return
        stamp = (self._state["session"], self._state["revision"], page)
        if page in self._text_layouts or stamp in self._text_pending: return
        self._text_pending.add(stamp)
        def got(data):
            self._text_pending.discard(stamp)
            if self.closed or not self.active or data.get("stale") or stamp[:2] != (self._state["session"], self._state["revision"]): return
            self._receive_annotations(page, data.get('annotations', []))
            self._text_layouts[page] = data
            self._text_layouts.move_to_end(page)
            while len(self._text_layouts) > 12:
                candidate = next(iter(self._text_layouts))
                if candidate == self._text_page:
                    self._text_layouts.move_to_end(candidate)
                    continue
                self._text_layouts.popitem(last=False)
            self._text_tick += 1
            self.textLayoutChanged.emit()
            if page == self._page: self.auto_timer.start()
        def failed(message):
            self._text_pending.discard(stamp)
            self.set_status("텍스트를 불러오지 못했어요: " + message)
        self.command("text_layout", {"page": page}, got, priority=8, guarded=True, error_callback=failed)

    @Slot(int, int, int)
    def selectCharacters(self, page, start, end):
        data = self._text_layouts.get(page, {})
        if not data.get("copyable"): return
        chars = data["chars"]
        start, end = sorted((max(0, min(len(chars), start)), max(0, min(len(chars), end))))
        text, last_line = [], None
        for char in chars[start:end]:
            if last_line is not None and char[5] != last_line: text.append("\n")
            text.append(char[0])
            last_line = char[5]
        self._text_page, self._text_start, self._text_end = page, start, end
        self._selected_text = "".join(text)
        self.textSelectionChanged.emit()
        self.set_status(f"{len(self._selected_text)}자 선택 · Ctrl+C 또는 우클릭으로 복사" if text else "글자를 드래그해서 선택하세요.")

    @Slot()
    def clearTextSelection(self):
        self._selected_text = ""
        self._text_page = -1
        self._text_start = self._text_end = 0
        self.textSelectionChanged.emit()

    @Slot()
    def selectAllText(self):
        data = self._text_layouts.get(self._page)
        if data: self.selectCharacters(self._page, 0, len(data["chars"]))

    def auto_recognize(self):
        if (self.workspace and self.workspace.closing) or not self.active or self.closed or not self._auto_ocr or self._merge_dialog_open or self._annotation_editor_open or self._text_editor_open or self._presentation_active or self._busy or self._ocr_busy or not self._state.get("editable"): return
        if self.hub and any(b is not self and b.ocrBusy for b in self.hub.controllers): return
        data = self._text_layouts.get(self._page, {})
        if not data.get("copyable") or data.get("hasText"): return
        key = (self._state["session"], data.get("pageId"))
        if key in self._auto_attempted: return
        self._auto_attempted.add(key)
        self.inspectOcr()
        languages = [x for x in ("kor", "eng") if x in self._languages]
        if languages:
            self.startOcr("current", "+".join(languages))

    @Slot()
    def recognizeCurrentPage(self):
        self.inspectOcr()
        language = "+".join(x for x in ("kor", "eng") if x in self._languages)
        self.startOcr("current", language)

    def set_status(self, message):
        self._status = message
        self.statusChanged.emit()

    def command(self, op, args=None, callback=None, priority=0, guarded=False, error_callback=None):
        if self.hub:
            return self.hub.command(self, op, args, callback, priority, guarded, error_callback)
        self.serial += 1
        self.callbacks[self.serial] = (callback, error_callback)
        msg = {"id": self.serial, "op": op, "args": args or {}, "priority": priority}
        if guarded:
            msg.update(session=self._state["session"], revision=self._state["revision"])
        self.inbox.put(msg)

    def poll(self):
        for _ in range(30):
            try:
                msg = self.outbox.get_nowait()
            except queue.Empty:
                break
            success, error = self.callbacks.pop(msg["id"], (None, None))
            if "error" in msg:
                if error:
                    error(msg["error"])
                else:
                    self.showError.emit(msg["error"])
            elif success:
                success(msg.get("result", {}))
        self.poll_ocr()
        self.poll_merge()

    def update_state(self, state):
        if state.get("stale"):
            return
        old_session, old_revision = self._state.get("session"), self._state.get("revision")
        previous_hit = self.activeSearchHit
        old_tokens = self._state.get("pageTokens") or []
        self._state = state
        self._image_focus = state.get("imageFocus", {})
        if 'annotationFocus' in state: self._annotation_focus = state['annotationFocus']
        elif old_session != state['session']: self._annotation_focus = {}
        self._busy = False
        if old_session != state["session"] or old_revision != state["revision"]:
            self.auto_timer.stop()
            self._annotation_token += 1
            self._annotation_loading = False
            self._annotation_pages.clear()
            self.annotationsChanged.emit()
            self._text_layouts.clear()
            self._text_pending.clear()
            self.clearTextSelection()
            if old_session != state["session"]: self._auto_attempted.clear()
            self._text_tick += 1
            self.textLayoutChanged.emit()
            if old_session != state["session"]:
                self.images.clear_session(old_session)
                self._sources.clear()
                self._metrics.clear()
            else:
                self._retain_unchanged_pages(state, old_tokens)
            self._pending_images.clear()
            self._render_queue.clear()
            self._requested_widths.clear()
            self._render_errors.clear()
            self._blocks = []
            self._page_blocks.clear()
            self._blocks_pending.clear()
            self._search_token += 1
            self._search = []
            self._hits = []
            self._hit_index = -1
            self._search_busy = False
            self._blocks_updated()
            self.searchChanged.emit()
            self._tick += 1
            self.imagesChanged.emit()
            self._request_outline()
        self._page = min(max(0, self._page), state["count"]-1)
        self._selection = [x for x in self._selection if x < state["count"]] or [self._page]
        self.stateChanged.emit()
        self.selectionChanged.emit()
        self.requestText(self._page)
        if self._annotation_panel_open: self.loadAnnotations()
        if self._query and not self._search and (old_session != state["session"] or old_revision != state["revision"]):
            self.search(self._query, navigate=False, restore=previous_hit)

    def failure(self, message):
        self._busy = False
        self.stateChanged.emit()
        self.set_status("변경을 적용하지 못했어요.")
        self.showError.emit(message)

    def edit(self, op, args):
        if self._busy or self._ocr_busy or not self._state["count"]:
            return
        self._busy = True
        self.stateChanged.emit()
        self.set_status("변경 사항을 적용하는 중…")
        def done(result):
            self.update_state(result)
            self.set_status("변경됨 · 저장하면 PDF에 반영됩니다.")
        self.command(op, args, done, error_callback=self.failure)

    def confirm_discard(self):
        if not self._state.get("dirty"):
            return True
        return QMessageBox.question(None, "저장하지 않은 변경", "저장하지 않은 변경 사항을 버릴까요?",
            QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Cancel) == QMessageBox.Discard

    @Slot()
    def chooseOpen(self):
        if self.workspace:
            self.workspace.chooseOpen()
            return
        if self._busy or self._ocr_busy:
            return
        path, _ = QFileDialog.getOpenFileName(None, "PDF 열기", "", "PDF 문서 (*.pdf)")
        if path: self.openPath(path)

    @Slot(str)
    def openPath(self, path):
        if self.workspace:
            self.workspace.openPaths([path])
            return
        self.open_current(path)

    def open_current(self, path):
        from PySide6.QtCore import QUrl
        if path.startswith("file:"):
            path = QUrl(path).toLocalFile()
        if self._busy or self._ocr_busy or not self.confirm_discard(): return
        self._busy = True
        self.stateChanged.emit()
        self.set_status("문서를 여는 중…")
        def opened(state):
            if state.get("passwordRequired"):
                password, ok = QInputDialog.getText(None, "암호가 필요한 PDF", "암호", QLineEdit.Password)
                if ok:
                    self.command("open", {"path": path, "password": password}, opened, error_callback=self.failure)
                else:
                    self._busy = False
                    self.stateChanged.emit()
                return
            self._page, self._selection = 0, [0]
            self.update_state(state)
            self.set_status("문서를 열었어요.  " + ("편집 가능" if state["editable"] else "읽기 전용"))
            library = self.library
            resume = library.opened(state["path"], state["name"], state["count"]) if library else 0
            if 0 < resume < state["count"]:
                self.resumeRequested.emit(resume)
                self.set_status("문서를 열었어요. 지난번에 읽던 %d페이지로 이동했어요." % (resume+1))
        self.command("open", {"path": path}, opened, error_callback=self.failure)

    @Slot(bool)
    def save(self, save_as=False):
        if not self._state["count"] or self._busy or self._ocr_busy: return
        path = self._state["path"]
        if save_as:
            original = Path(path)
            path, _ = QFileDialog.getSaveFileName(None, "PDF 다른 이름으로 저장",
                str(original.with_name(original.stem + "_편집.pdf")), "PDF 문서 (*.pdf)")
            if not path: return
        if self.workspace and self.workspace.other_open(path, self):
            self.showError.emit("이 경로의 PDF가 다른 탭에 열려 있어요. 다른 파일 이름으로 저장해 주세요.")
            return
        self._busy = True
        self.stateChanged.emit()
        self.set_status("PDF를 저장하고 검증하는 중…")
        def done(state):
            self.update_state(state)
            if self.library: self.library.opened(state["path"], state["name"], state["count"])
            self.remember_page()
            self.set_status("저장 완료 · " + state["name"])
        self.command("save", {"path": path}, done, error_callback=self.failure)

    @Property(str, notify=preferencesChanged)
    def themeMode(self):
        value = str(self.preferences.value("themeMode", "system"))
        return value if value in ("system", "light", "dark") else "system"

    @Slot(str)
    def setThemeMode(self, value):
        if value in ("system", "light", "dark"):
            self.preferences.setValue("themeMode", value)
            self.preferencesChanged.emit()

    @Property(str,notify=preferencesChanged)
    def graphicsMode(self):return self.preferences.value("graphicsMode","auto")
    @Slot(str)
    def setGraphicsMode(self,value):
        self.preferences.setValue("graphicsMode","software" if value=="software" else "auto")
        self.preferencesChanged.emit()

    @Property(int, notify=preferencesChanged)
    def cacheMiB(self): return self.images.budget//(1024*1024)

    @Slot(int)
    def setCacheMiB(self,value):
        value = min(1024,max(256,value))
        self.images.budget=value*1024*1024;self.images.trim()
        self.preferences.setValue("cacheMiB",value);self.preferencesChanged.emit()

    def _page_token(self, page, state=None):
        tokens = (state or self._state).get("pageTokens") or []
        # Older engines without tokens fall back to revision-wide invalidation.
        return tokens[page] if 0 <= page < len(tokens) else f'r{(state or self._state)["revision"]}p{page}'

    def _image_key(self,page,kind,width):
        return f'{self._state["session"]}-{self._page_token(page)}-{kind}-{width}'

    def _retain_unchanged_pages(self, state, previous):
        """After an edit, keep every rendered page whose content did not change.

        Only edited pages are drawn again; moved pages reuse their images, and
        an edited page keeps showing its previous image until the new one is
        ready, instead of every page and thumbnail going blank."""
        old_tokens = set(previous)
        count = state["count"]
        for (page, kind), key in list(self._sources.items()):
            parts = key.split("-")
            token = parts[1] if len(parts) >= 4 else ""
            if page >= count:
                del self._sources[(page, kind)]
                continue
            new = self._page_token(page, state)
            if token == new: continue
            # Same slot, new content: keep the old picture as a placeholder.
            # Content moved from elsewhere: the old picture would be wrong.
            if new in old_tokens: del self._sources[(page, kind)]
        live = set(state.get("pageTokens") or [])
        self._metrics = {t: m for t, m in self._metrics.items() if t in live}

    def _publish_image(self,page,kind,key):
        if self._sources.get((page,kind)) == key: return
        self._sources[(page,kind)]=key
        self._tick+=1
        self.imagesChanged.emit()
        self.pageImageChanged.emit(page,kind)

    @Slot(int, str, int)
    def requestPage(self,page,kind,width):
        if not self.active or self.closed: return
        if not 0 <= page < self._state["count"]:return
        width=min(3600,max(128,((int(width)+63)//64)*64))
        key=self._image_key(page,kind,width)
        self._requested_widths[(page,kind)] = width
        # A cache hit must reconnect the image to the delegate. The old version
        # returned here without doing so, leaving blank/stale previews.
        if self.images.get(key) is not None:
            self._publish_image(page,kind,key)
            return
        for old,request in list(self._render_queue.items()):
            if request[:2] == (page,kind) and request[2] != width:
                del self._render_queue[old];self._pending_images.discard(old)
        # A fast first frame is followed by the display-resolution frame.
        if kind in ("main", "presentation") and width>640 and not self.imageUrl(page,kind):
            preview=self._image_key(page,kind,640)
            if self.images.get(preview) is not None:self._publish_image(page,kind,preview)
            elif preview not in self._pending_images:
                self._render_queue[preview]=(page,kind,640,True)
                self._pending_images.add(preview)
        if key not in self._pending_images:
            self._pending_images.add(key)
            self._render_queue[key]=(page,kind,width,False)
        if not self._render_scheduled:
            self._render_scheduled=True
            QTimer.singleShot(0,self._resume_render)

    @Slot(int,str,int)
    def retryPage(self,page,kind,width):
        self._render_errors.pop((page,kind),None)
        self.pageImageChanged.emit(page,kind)
        self.requestPage(page,kind,width)

    @Slot(bool)
    def setPresentationActive(self, active):
        self._presentation_active = bool(active)
        if active:
            self.auto_timer.stop()
            # A search already in flight may finish, but must not move a slide.
            self._search_waiting = None
        elif self.active and not self.closed: self.auto_timer.start()

    @Slot(int,str)
    def releasePage(self,page,kind):
        for key,request in list(self._render_queue.items()):
            if request[:2] == (page,kind):
                del self._render_queue[key];self._pending_images.discard(key)

    def _resume_render(self):
        if self.hub: self.hub.pump()
        else: self._pump_render()

    def set_active(self, active):
        self.active = active
        if active:
            # Settings are application-wide, while document state is independent.
            self._auto_ocr = self.preferences.value("automaticOcr", True, type=bool)
            self._wheel_speed = float(self.preferences.value("wheelSpeed", 1.0))
            self.preferencesChanged.emit()
            self.requestText(self._page)
            if self._annotation_panel_open: self.loadAnnotations()
            self.auto_timer.start()
            self._resume_render()
        else:
            self.auto_timer.stop()
            self._annotation_token += 1
            self._annotation_loading = False
            for key in self._render_queue: self._pending_images.discard(key)
            self._render_queue.clear()
            # Hidden tabs retain PDF/history, not text geometry for twelve pages.
            self._text_layouts.clear()
            self._text_tick += 1

    def _pump_render(self):
        self._render_scheduled=False
        if not self.active or self.closed: return
        def priority(request):
            page,kind,width,preview=request
            if kind=="thumb":return 4+min(abs(page-self._page),8)
            return (0 if preview else 2) + min(abs(page-self._page),8)*3
        while self._render_queue:
            slot=self.frames.acquire()
            if slot is None:return
            index,frame=slot
            key=min(self._render_queue,key=lambda k:priority(self._render_queue[k]))
            page,kind,width,preview=self._render_queue.pop(key)
            def done(result,key=key,page=page,kind=kind,index=index,preview=preview,width=width):
                try:
                    # Images are keyed by page content, so a frame finished after
                    # an unrelated edit is still valid for the key it was asked for.
                    if self.closed or not self.active or result.get("stale") or result.get("session")!=self._state["session"]:return
                    image=self.frames.image(index,result)
                    if image.isNull():raise RuntimeError("빈 페이지 이미지입니다.")
                    self.images.put(key,image)
                    if key.split("-")[1]!=self._page_token(page):return  # page changed since the request
                    metrics=(result["pageWidth"],result["pageHeight"])
                    token=result.get("token") or self._page_token(page)
                    if self._metrics.get(token)!=metrics:
                        self._metrics[token]=metrics
                        if self._page_token(page)==token:self.pageMetricsChanged.emit(page)
                    target=self._image_key(page,kind,self._requested_widths.get((page,kind),width))
                    if self.images.get(target) is not None:self._publish_image(page,kind,target)
                    elif not self.imageUrl(page,kind) or not preview:self._publish_image(page,kind,key)
                    self._render_errors.pop((page,kind),None)
                except Exception as exc:
                    self.set_status(f"{page+1}페이지 미리보기: {exc}")
                finally:
                    self._pending_images.discard(key);self.frames.release(index)
                    QTimer.singleShot(0,self._resume_render)
            def failed(error,key=key,page=page,kind=kind,index=index):
                self._pending_images.discard(key);self.frames.release(index)
                self._render_errors[(page,kind)]=error
                self.pageImageChanged.emit(page,kind)
                self.set_status(f"{page+1}페이지를 그리지 못했어요: {error}")
                QTimer.singleShot(0,self._resume_render)
            self.command("render_frame",{"page":page,"width":width,"shared_name":frame.name if frame else ""},done,
                         priority=5,guarded=True,error_callback=failed)

    @Slot(int,str,result=str)
    def imageUrl(self,page,kind):
        key=self._sources.get((page,kind),"")
        return "image://pages/"+key if self.images.get(key) is not None else ""

    @Slot(int,str,result=str)
    def imageError(self,page,kind):return self._render_errors.get((page,kind),"")

    @Slot(int, result=float)
    def pageRatio(self, page):
        w, h = self._metrics.get(self._page_token(page), self._state.get("size", [595, 842]))
        return h / w

    @Slot(int, result=float)
    def pageWidth(self, page):
        return self._metrics.get(self._page_token(page), self._state.get("size", [595, 842]))[0]

    @property
    def library(self):
        return getattr(self.workspace, "library", None) if self.workspace else None

    def remember_page(self):
        if self.library and self._state.get("count"):
            self.library.remember(self._state.get("path", ""), self._page)

    def _request_outline(self):
        self._outline_token += 1
        token = self._outline_token
        if self._outline:
            self._outline = []
            self.outlineChanged.emit()
        if not self._state.get("count") or self.closed: return
        def got(result):
            if token != self._outline_token or self.closed or result.get("stale"): return
            self._outline = result.get("items", [])
            self.outlineChanged.emit()
        def failed(message):
            if token == self._outline_token: self._outline = []; self.outlineChanged.emit()
        self.command("outline", {}, got, priority=9, guarded=True, error_callback=failed)

    @Property('QVariantList', notify=outlineChanged)
    def outline(self): return self._outline

    @Slot(int)
    def openOutline(self, index):
        if not 0 <= index < len(self._outline): return
        item = self._outline[index]
        if 0 <= item["page"] < self._state["count"]:
            self.outlineRequested.emit(item["page"], float(item.get("y", 0)))

    @Slot(int)
    def setCurrentPage(self, page):
        if 0 <= page < self._state["count"] and page != self._page:
            self._page = page
            self.remember_page()
            self._blocks = []
            self._blocks_updated()
            self.selectionChanged.emit()
            self.textLayoutChanged.emit()
            self.requestText(page)
            self.auto_timer.start()

    @Slot(int, bool, bool)
    def selectPage(self, page, control=False, shift=False):
        if not 0 <= page < self._state["count"]: return
        if shift and self._selection:
            anchor = self._selection_anchor
            self._selection = list(range(min(anchor, page), max(anchor, page)+1))
        elif control:
            self._selection = ([x for x in self._selection if x != page]
                               if page in self._selection else self._selection + [page])
        else:
            self._selection = [page]
        if not shift: self._selection_anchor=page
        self._page = page
        self.remember_page()
        self._blocks = []
        self._blocks_updated()
        self.selectionChanged.emit()

        self.textLayoutChanged.emit()
        self.requestText(page)
        self.auto_timer.start()

    @Slot(int)
    def selectPointer(self, page):
        from PySide6.QtGui import QGuiApplication
        modifiers = QGuiApplication.keyboardModifiers()
        self.selectPage(page, bool(modifiers & Qt.ControlModifier), bool(modifiers & Qt.ShiftModifier))

    @Slot(int, int)
    def movePage(self, source, target):
        if source == target: return
        self._page, self._selection = target, [target]
        self.edit("move_page", {"source": source, "target": target})

    @Slot(int)
    def moveSelectionTo(self, target):
        if self.busy or self.ocrBusy or self._text_editor_open or self._annotation_editor_open: return
        selected=self._selection or [self._page]
        self._busy=True;self.stateChanged.emit()
        def done(state):
            self._selection=state.get('movedSelection',selected)
            self._page=self._selection[0];self._selection_anchor=self._page
            self.update_state(state)
            self.set_status(f"{len(self._selection)}페이지를 함께 이동했어요. Ctrl+Z로 되돌릴 수 있어요.")
        self.command('move_pages',{'pages':selected,'target':target,'revision':self._state['revision']},done,error_callback=self.failure)

    @Slot(int)
    def moveSelected(self, delta):
        selected=sorted(self._selection or [self._page])
        target=selected[0]-1 if delta<0 else selected[-1]+2
        if 0<=target<=self._state['count']: self.moveSelectionTo(target)

    @Slot()
    def deleteSelected(self):
        pages = self._selection or [self._page]
        if not pages: return
        if QMessageBox.question(None, "페이지 삭제", f"선택한 {len(pages)}페이지를 삭제할까요? 실행 취소할 수 있어요.",
             QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            self.edit("delete_pages", {"pages": pages})

    @Slot()
    def rotateSelected(self): self.edit("rotate", {"pages": self._selection or [self._page]})
    @Slot()
    def undo(self): self.edit("undo", {})
    @Slot()
    def redo(self): self.edit("redo", {})

    @Property('QVariantList',notify=mergeChanged)
    def mergeItems(self):
        return [{k:v for k,v in item.items() if k!='password'} for item in self._merge_items]
    @Property(bool,notify=mergeChanged)
    def mergeBusy(self):return self._merge_busy
    @Property(bool,notify=mergeChanged)
    def mergeInspecting(self):return self._merge_inspecting>0
    @Property(str,notify=mergeChanged)
    def mergeProgress(self):return self._merge_progress
    @Property(str,notify=mergeChanged)
    def mergeResult(self):return self._merge_result
    @Property(int,notify=mergeChanged)
    def mergePageCount(self):return sum(item['count'] for item in self._merge_items)

    @Slot()
    def showMerge(self):
        if self._busy or self._ocr_busy:return
        self._merge_dialog_open=True;self.auto_timer.stop()
        for item in self._merge_items:
            if item.get('live') and item['session']==self._state['session']:
                item.update(count=self._state['count'],path=self._state['path'],name=self._state['name'],preview=self.imageUrl(0,'thumb'))
        self._merge_result="";self.mergeChanged.emit();self.openMergeDialog.emit()

    @Slot()
    def closeMerge(self):
        self._merge_dialog_open=False;self.auto_timer.start()

    @Slot()
    def chooseMergeFiles(self):
        if self._merge_busy:return
        paths,_=QFileDialog.getOpenFileNames(None,"결합할 PDF 추가","","PDF 문서 (*.pdf)")
        self.addMergePaths(paths)

    @Slot('QVariantList')
    def addMergePaths(self,paths):
        from PySide6.QtCore import QUrl
        if self._merge_busy:return
        for path in paths:
            path=path.toLocalFile() if isinstance(path,QUrl) else str(path)
            if path.startswith('file:'):path=QUrl(path).toLocalFile()
            if not path.lower().endswith('.pdf'):continue
            self._inspect_merge_path(path)

    def _inspect_merge_path(self,path,password="",token=None):
        token=token or uuid.uuid4().hex
        self._merge_inspecting+=1;self.mergeChanged.emit()
        def done(data):
            self._merge_inspecting-=1
            if data.get('passwordRequired'):
                self.mergeChanged.emit()
                password2,ok=QInputDialog.getText(None,"PDF 암호",Path(path).name,QLineEdit.Password)
                if ok:self._inspect_merge_path(path,password2,token)
                return
            key='merge-thumb-'+token
            self.images.put(key,data.pop('preview'))
            data.update(id=token,password=password,preview='image://pages/'+key,live=False)
            self._merge_items.append(data);self._merge_result="";self.mergeChanged.emit()
        def failed(message):
            self._merge_inspecting-=1;self.mergeChanged.emit();self.showError.emit(Path(path).name+"\n"+message)
        self.command('inspect_merge',{'path':path,'password':password},done,priority=12,error_callback=failed)

    @Slot()
    def addCurrentToMerge(self):
        if self._merge_busy or not self._state['count']:return
        if any(x.get('live') for x in self._merge_items):return
        self._merge_items.append({'id':uuid.uuid4().hex,'name':self._state['name'],
            'path':self._state['path'],'count':self._state['count'],'bytes':0,
            'preview':self.imageUrl(0,'thumb'),'live':True,'session':self._state['session']})
        self._merge_result="";self.mergeChanged.emit()

    @Slot(int,int)
    def moveMergeItem(self,source,target):
        if self._merge_busy:return
        if 0<=source<len(self._merge_items) and 0<=target<len(self._merge_items):
            self._merge_items.insert(target,self._merge_items.pop(source));self.mergeChanged.emit()
    @Slot(int)
    def removeMergeItem(self,index):
        if not self._merge_busy and 0<=index<len(self._merge_items):
            self._merge_items.pop(index);self.mergeChanged.emit()

    @Slot()
    def chooseMergeOutput(self):
        if self._merge_busy or self._busy or self._ocr_busy or self._merge_inspecting or len(self._merge_items)<2:return
        path,_=QFileDialog.getSaveFileName(None,"결합한 PDF 저장","결합한 문서.pdf","PDF 문서 (*.pdf)")
        if path:self.startMergeTo(path)

    def startMergeTo(self,path):
        from .merging import merge_files
        if self._busy or self._ocr_busy or self._merge_busy or self._merge_inspecting or len(self._merge_items)<2:return
        path=str(Path(path).with_suffix('.pdf').resolve())
        if self.workspace and self.workspace.other_open(path, self):
            self.showError.emit("이 경로의 PDF가 다른 탭에 열려 있어요. 다른 이름으로 결합해 주세요.")
            return
        originals=[x['path'] for x in self._merge_items]+([self._state['path']] if self._state['count'] else [])
        if any(Path(x).resolve()==Path(path) or (Path(path).exists() and Path(x).exists() and os.path.samefile(x,path)) for x in originals):
            self.showError.emit("원본과 다른 이름으로 결합 파일을 저장해 주세요.");return
        items=[dict(x) for x in self._merge_items]
        if any(x.get('live') and x['session']!=self._state['session'] for x in items):
            self.showError.emit("열린 문서가 바뀌었어요. 목록에서 현재 문서를 다시 추가해 주세요.");return
        self._merge_busy=True;self._busy=True;self.auto_timer.stop()
        self._merge_result="";self._merge_progress="결합 준비 중…"
        self.merge_cancel=self.ctx.Event();self.mergeChanged.emit();self.stateChanged.emit()
        def started(snapshot=None):
            try:
                if snapshot:
                    self._merge_snapshot=snapshot['path']
                    for item in items:
                        if item.get('live'):
                            item['originalPath']=item['path'];item['path']=snapshot['path'];item['password']=snapshot.get('password','')
                if self.merge_cancel.is_set():self.finish_merge();return
                fd,self._merge_temp=tempfile.mkstemp(prefix='.bichaek-merge-',suffix='.pdf',dir=str(Path(path).parent));os.close(fd)
                self.merge_events=self.ctx.Queue()
                self.merge_process=self.ctx.Process(target=merge_files,args=(items,path,self._merge_temp,self.merge_events,self.merge_cancel))
                self.merge_process.start()
            except Exception as exc:self.finish_merge(str(exc))
        if any(x.get('live') for x in items):
            self.command('ocr_snapshot',{},started,error_callback=self.finish_merge)
        else:started()

    @Slot()
    def cancelMerge(self):
        if self.merge_cancel:
            self.merge_cancel.set();self._merge_progress="현재 파일 처리가 끝나면 취소합니다…";self.mergeChanged.emit()

    def poll_merge(self):
        if self.merge_events is None:return
        for _ in range(10):
            try:msg=self.merge_events.get_nowait()
            except queue.Empty:break
            if 'progress' in msg:
                self._merge_progress=f"{msg['progress']} / {msg['total']}개 파일 · {msg['pages']}페이지 결합 중"
                self.mergeChanged.emit()
            if msg.get('done'):
                self._merge_result=msg['path'];self.finish_merge()
                self.set_status(f"PDF 결합 완료 · {msg['pages']}페이지");return
            if msg.get('cancelled'):self.finish_merge();self.set_status("PDF 결합을 취소했어요.");return
            if 'error' in msg:self.finish_merge(msg['error']);return

    def finish_merge(self,error=""):
        if self.merge_process:self.merge_process.join(timeout=1)
        if self._merge_snapshot:self.command('release_snapshot',{'path':self._merge_snapshot});self._merge_snapshot=None
        if self._merge_temp:Path(self._merge_temp).unlink(missing_ok=True);self._merge_temp=None
        self.merge_process=self.merge_events=self.merge_cancel=None
        self._merge_busy=False;self._busy=False;self._merge_progress=""
        self.mergeChanged.emit();self.stateChanged.emit();self.auto_timer.start()
        if error:self.showError.emit(error)

    @Slot()
    def insertPdf(self):
        path, _ = QFileDialog.getOpenFileName(None, "현재 페이지 뒤에 PDF 삽입", "", "PDF 문서 (*.pdf)")
        if path: self.edit("insert_pdf", {"path": path, "at": self._page+1})

    @Slot(int, result='QVariantList')
    def blocksAt(self, page): return self._page_blocks.get(page,[])

    @Slot(int, result='QVariantList')
    def blockBoxes(self, page):
        """What QML needs to draw clickable paragraph boxes. The full blocks
        carry every character's coordinates; copying those into QML on each
        refresh is what made entering edit mode slow on dense pages."""
        return [{"id": b["id"], "page": b.get("page", page), "displayRect": b["displayRect"]}
                for b in self._page_blocks.get(page, [])]

    @Property(int, notify=blocksChanged)
    def blocksTick(self): return self._blocks_tick

    def _blocks_updated(self):
        # QML depends on this counter, not on the block list itself.
        self._blocks_tick += 1
        self.blocksChanged.emit()

    @Slot(int)
    def loadBlocks(self, page):
        self.loadBlocksForPage(page)
        if page in self._page_blocks:
            if self._blocks is not self._page_blocks[page]:
                self._blocks=self._page_blocks[page];self._blocks_updated()

    @Slot(int)
    def loadBlocksForPage(self, page):
        if not 0<=page<self._state['count'] or page in self._page_blocks: return
        stamp=(self._state['session'],self._state['revision'],page)
        if stamp in self._blocks_pending:return
        self._blocks_pending.add(stamp)
        def done(result):
            self._blocks_pending.discard(stamp)
            if result.get('stale') or self.closed or stamp[:2]!=(self._state['session'],self._state['revision']):return
            self._page_blocks[page]=result['blocks']
            if page==self._page:self._blocks=result['blocks']
            if len(self._page_blocks)>12:
                for key in list(self._page_blocks):
                    if key!=self._page and key!=page:
                        self._page_blocks.pop(key);break
            self._blocks_updated()
        def failed(message):
            self._blocks_pending.discard(stamp);self.set_status(message)
        self.command('objects',{'page':page},done,priority=2,guarded=True,error_callback=failed)

    @Property(str, notify=fontsChanged)
    def editorFontFamily(self): return self._editor_font_family

    @Property(QObject,constant=True)
    def liveEditor(self):return self._live_editor

    def _font_preview(self):
        if self._live_editor.target:
            self._live_editor.loadFonts();return
        self._font_preview_token+=1;token=self._font_preview_token
        self._editor_font_family=''
        if not self._editing_target:return
        target=self._editing_target
        def got(result):
            if self.closed or token!=self._font_preview_token or result.get('stale'):return
            import hashlib
            data=result.get('font',b'')
            if not data:return
            key=hashlib.sha256(data).hexdigest()
            if key not in self._qt_font_ids:
                self._qt_font_ids[key]=QFontDatabase.addApplicationFontFromData(QByteArray(data))
            families=QFontDatabase.applicationFontFamilies(self._qt_font_ids[key])
            if families:self._editor_font_family=families[0];self.fontsChanged.emit()
        self.command('font_preview',{'page':target['page'],'name':target.get('font',''),
            'text':target.get('text',''),'source':self._font_choice,'path':self._font_path},got,
            guarded=True,error_callback=lambda message:None)


    FALLBACK_NAMES = ("malgun gothic", "맑은 고딕", "apple sd gothic neo", "noto sans cjk kr", "noto sans kr",
                      "nanumgothic", "나눔고딕", "source han sans k")

    def _fallback_row(self):
        """A regular Korean UI face that looks at home beside Latin text."""
        for wanted in self.FALLBACK_NAMES:
            for row in self._font_options:
                names = [row.get("label", ""), row.get("family", "")] + list(row.get("aliases", []))
                style = str(row.get("style", "Regular")).casefold()
                if style in ("regular", "normal", "book") and any(n.casefold() == wanted for n in names):
                    return row
        return None

    def fallback_font_path(self):
        row = self._fallback_row()
        return row["key"] if row else ""

    def fallback_label(self):
        row = self._fallback_row()
        return row.get("family") or row["label"] if row else "기본 한글 글꼴"

    @Property('QVariantList', notify=fontsChanged)
    def fontOptions(self):
        return ([{"label":"원본 글꼴 유지", "key":"original"}] if self._original_font_available else []) + [
                {"label":"기본 글꼴 · 한글 지원", "key":"default"}] + self._font_options

    @Property(int, notify=fontsChanged)
    def fontChoiceIndex(self):
        return next((i for i, f in enumerate(self.fontOptions) if f["key"] == self._font_choice), 0)

    @Slot(str)
    def setFontChoice(self, key):
        self._font_choice = key
        self._font_path = key if key not in ("original", "default") else ""
        self._font_preview()
        self.fontsChanged.emit()

    @Slot(bool)
    def setTextEditorVisible(self, visible):
        self._text_editor_open = visible
        if visible: self.auto_timer.stop()
        else:
            self._live_editor.stop()
            if self.active:self.auto_timer.start()

    def prepare_fonts(self, original):
        self._original_font_available = original
        self.setFontChoice("original" if original else "default")
        def got(result):
            if self.closed: return
            self._font_options = result["fonts"]
            if self._font_path and not any(f["key"] == self._font_path for f in self._font_options):
                self._font_options.append({"key":self._font_path, "label":Path(self._font_path).stem + " · 직접 선택"})
            self.fontsChanged.emit()
        self.command("available_fonts", callback=got, priority=15)

    @Slot('QVariantMap')
    def editBlock(self, block):
        if self._text_editor_open or self._annotation_editor_open: return
        page = block.get("page", self._page)
        full = next((b for b in self._page_blocks.get(page, []) if b["id"] == block.get("id")), None)
        value = dict(full if full is not None else block)
        value["session"] = self._state["session"]
        value["page"] = value.get("page", self._page)
        value["revision"] = self._state["revision"]
        value["mode"] = "replace"
        value['pageWidth']=self.pageWidth(value['page']) if value.get('rotation',0)%180==0 else self.pageWidth(value['page'])*self.pageRatio(value['page'])
        value['pageHeight']=self.pageWidth(value['page'])*self.pageRatio(value['page']) if value.get('rotation',0)%180==0 else self.pageWidth(value['page'])
        value['neighbors']=[b['rect'] for b in self._page_blocks.get(value['page'],[]) if b['id']!=value['id']]
        self._editing_target=value
        self._live_editor.start(value)
        self.prepare_fonts(True)
        self.showTextEditor.emit(value)

    @Slot('QVariantMap', str, float, float)
    def applyText(self, target, text, size, height):
        target = dict(target)
        if self.busy or self.ocrBusy: return
        if target.get('mode')=='replace' and self._live_editor.target:
            self._live_editor.setSize(size);self._live_editor.apply();return
        if target.get("session", self._state["session"]) != self._state["session"] or target.get("revision", self._state["revision"]) != self._state["revision"]:
            self.showError.emit("문서가 변경되었어요. 텍스트를 다시 선택해 주세요.")
            return
        if target.get("mode") == "replace":
            op = "replace_text"
            args = {"page": target["page"], "block_id": target["id"],
                "text": text, "size": size, "height": height, "color": target.get("color", 0x202124),
                "font_path": self._font_path, "font_source": self._font_choice, "revision": target["revision"]}
        else:
            op = "add_text"
            rect = list(target["rect"])
            rect[3] = rect[1] + height
            args = {"page": target["page"], "rect": rect, "text": text,
                    "size": size, "font_path": self._font_path}
        self._busy = True
        self.stateChanged.emit()
        def done(state):
            self.update_state(state)
            self.set_status("텍스트를 적용했어요. Ctrl+S로 저장하세요.")
            self.textCommitted.emit()
        self.command(op, args, done, error_callback=self.failure)

    @Slot()
    def chooseImage(self):
        if not self._state.get("editable") or self.busy or self.ocrBusy: return
        page = self._page
        path, _ = QFileDialog.getOpenFileName(None, "이미지 삽입", "", "이미지 (*.png *.jpg *.jpeg *.tif *.tiff *.bmp)")
        if not path: return
        reader = QImageReader(path)
        size = reader.size()
        if not size.isValid():
            self.showError.emit("이미지 파일을 읽을 수 없어요.")
            return
        width = self.pageWidth(page)
        height = width * self.pageRatio(page)
        factor = min(width*.65/size.width(), height*.5/size.height(), .75)
        iw, ih = size.width()*factor, size.height()*factor
        rect = [(width-iw)/2, (height-ih)/2, (width+iw)/2, (height+ih)/2]
        self._busy = True
        self.stateChanged.emit()
        def done(state):
            self.update_state(state)
            self.set_status("이미지를 삽입했어요. Ctrl+S로 저장하거나 Ctrl+Z로 되돌릴 수 있어요.")
            if self.active:
                self.imageInserted.emit()
                self.navigateRequested.emit(page, rect[0], rect[1])
        self.command("add_image", {"page":page, "rect":rect, "path":path}, done, error_callback=self.failure)

    @Property('QVariantMap', notify=stateChanged)
    def imageFocus(self): return self._image_focus

    @Slot('QVariantMap', 'QVariantList')
    def transformImage(self, data, rect):
        if self._text_editor_open or self._annotation_editor_open: return
        data=dict(data)
        self.edit('transform_image',{'page':data['page'],'identifier':data['id'],'rect':list(rect),
            'session':data['session'],'revision':data['revision']})

    @Slot('QVariantMap', 'QVariantList')
    def moveAnnotation(self, data, point):
        if self._text_editor_open or self._annotation_editor_open: return
        data=dict(data)
        self.edit('move_annotation',{'page':data['page'],'identifier':data['id'],'point':list(point),
            'session':data['session'],'revision':data['revision']})

    @Slot('QVariantMap')
    def deleteAnnotationAt(self, data):
        if self._text_editor_open or self._annotation_editor_open: return
        data=dict(data)
        if data.get('session')!=self._state['session'] or data.get('revision')!=self._state['revision']:
            self.showError.emit('문서가 바뀌었어요. 주석을 다시 선택해 주세요.');return
        self.edit('delete_annotation',{'page':data['page'],'identifier':data['id'],'revision':data['revision']})

    @Slot('QVariantMap', bool)
    def exportImage(self, image, save):
        image = dict(image)
        if not image or self.closed: return
        stamp = (self._state["session"], self._state["revision"])
        if (image.get("session"), image.get("revision")) != stamp:
            self.showError.emit("문서가 변경되었어요. 이미지를 다시 선택해 주세요.")
            return
        path = ""
        if save:
            name = Path(self._state["path"]).stem + f'-p{image["page"]+1}-image{image["number"]+1}.png'
            path, _ = QFileDialog.getSaveFileName(None, "이미지를 PNG로 저장", name, "PNG 이미지 (*.png)")
            if not path: return
            if not Path(path).suffix: path += ".png"
            if Path(path).suffix.lower() != ".png":
                self.showError.emit("파일 이름의 확장자를 .png로 지정해 주세요.")
                return
        def got(result):
            if self.closed or stamp != (self._state["session"], self._state["revision"]): return
            if result.get("stale"): return
            data = result["png"]
            if save:
                output = QSaveFile(path)
                if not output.open(QIODevice.WriteOnly) or output.write(data) != len(data) or not output.commit():
                    self.showError.emit("이미지를 저장하지 못했어요: " + output.errorString())
                    return
                self.set_status("이미지를 저장했어요: " + str(path))
            else:
                decoded = QImage.fromData(data, "PNG")
                if decoded.isNull():
                    self.showError.emit("이미지를 클립보드로 변환하지 못했어요.")
                    return
                QGuiApplication.clipboard().setImage(decoded)
                self.set_status(f'이미지를 복사했어요 · {result["width"]} × {result["height"]} px')
        self.command("extract_embedded_image", {"page":image["page"], "number":image["number"],
            "revision":image["revision"], "session":image["session"], "page_id":image["pageId"]}, got,
            error_callback=self.showError.emit)

    @Slot(int, 'QVariantList', str)
    def regionAction(self, page, rect, tool):
        rect = list(rect)
        if tool == "read":
            def got(result):
                self._selected_text = result.get("text", "")
                self.set_status(f"텍스트 {len(self._selected_text)}자 선택됨 · Ctrl+C로 복사" if self._selected_text else "선택 가능한 글자가 없어요. 스캔 문서는 OCR을 실행해 주세요.")
            self.command("selected_text", {"page": page, "rect": rect}, got, guarded=True)
        elif tool == "addText":
            self._editing_target={"page":page}
            self.prepare_fonts(False)
            self.showTextEditor.emit({"mode": "add", "page": page, "rect": rect,
                "text": "", "size": 14, "height": rect[3]-rect[1],
                "session": self._state["session"], "revision": self._state["revision"]})
        elif tool == "highlight": self.edit("highlight", {"page": page, "rect": rect})
        elif tool == "image":
            path, _ = QFileDialog.getOpenFileName(None, "이미지 삽입", "", "이미지 (*.png *.jpg *.jpeg *.tif *.tiff *.bmp)")
            if path: self.edit("add_image", {"page": page, "rect": rect, "path": path})
        elif tool == "note": self.composeComment(page, rect[0], rect[1])

    @Property(bool, notify=stateChanged)
    def canAnnotate(self):
        return bool(self._state.get('annotatable') and not self._busy and not self._ocr_busy)

    @Property(str, notify=preferencesChanged)
    def annotationAuthor(self): return self.preferences.value('annotationAuthor', '사용자')

    @Slot(str)
    def setAnnotationAuthor(self, value):
        self.preferences.setValue('annotationAuthor', value.strip() or '사용자')
        self.preferencesChanged.emit()

    @Property(str, notify=preferencesChanged)
    def annotationColor(self): return self.preferences.value('annotationColor', '#ffd54f')

    @Slot(str)
    def setAnnotationColor(self, value):
        from .annotations import color_rgb
        try: color_rgb(value)
        except ValueError: return
        self.preferences.setValue('annotationColor', value)
        self.preferencesChanged.emit()

    @Property(bool, notify=annotationsChanged)
    def annotationsLoading(self): return self._annotation_loading

    @Property('QVariantList', notify=annotationsChanged)
    def annotations(self):
        flat = [a for page in sorted(self._annotation_pages) for a in self._annotation_pages[page]]
        # Place nested replies immediately below the parent. Malformed cycles
        # and missing parents are still listed once, without infinite recursion.
        children, roots, seen, result = {}, [], set(), []
        ids = {(a['page'], a['id']) for a in flat}
        for a in flat:
            parent = (a['page'], a['parentId'])
            if a['reply'] and parent in ids: children.setdefault(parent, []).append(a)
            else: roots.append(a)
        def append_tree(a, depth=0):
            key = (a['page'], a['id'])
            if key in seen: return
            seen.add(key); result.append(dict(a, depth=min(depth, 4)))
            # Iterative depth is capped independently of malformed PDF threads.
            for child in children.get(key, []):
                if depth < 30: append_tree(child, depth+1)
        for a in roots+flat: append_tree(a)
        return result

    @Property('QVariantMap', notify=annotationsChanged)
    def selectedAnnotation(self):
        return next((a for a in self.annotations if a['id'] == self._annotation_focus.get('id') and
                     a['page'] == self._annotation_focus.get('page')), {})

    @Slot(int, result='QVariantList')
    def pageAnnotations(self, page): return self._annotation_pages.get(page, [])

    def _receive_annotations(self, page, items):
        self._annotation_pages[page] = items
        self.annotationsChanged.emit()

    @Slot(bool)
    def setAnnotationPanelVisible(self, visible):
        if self._annotation_panel_open == visible: return
        self._annotation_panel_open = visible
        if visible: self.loadAnnotations()
        else:
            self._annotation_token += 1
            self._annotation_loading = False
            self.annotationsChanged.emit()

    @Slot()
    def loadAnnotations(self):
        if not self._state['count'] or not self.active or self.closed: return
        self._annotation_token += 1
        token = self._annotation_token
        self._annotation_loading = True
        self.annotationsChanged.emit()
        def scan(page):
            if token != self._annotation_token or not self.active or self.closed: return
            while page < self._state['count'] and page in self._annotation_pages: page += 1
            if page >= self._state['count']:
                self._annotation_loading = False
                self.annotationsChanged.emit()
                return
            def got(result):
                if token != self._annotation_token or result.get('stale') or self.closed: return
                self._receive_annotations(page, result['items'])
                scan(page+1)
            def failed(message):
                if token == self._annotation_token:
                    self._annotation_loading = False
                    self.annotationsChanged.emit()
                    self.set_status('주석을 불러오지 못했어요: '+message)
            self.command('annotations_page', {'page':page}, got, priority=12, guarded=True, error_callback=failed)
        scan(0)

    @Slot(int, str)
    def selectAnnotation(self, page, identifier):
        self._annotation_focus = {'page':page, 'id':identifier}
        self.annotationsChanged.emit()
        item = self.selectedAnnotation
        if item:
            self.openComments.emit()
            self.navigateRequested.emit(page, item['rect'][0], item['rect'][1])

    @Slot(str)
    def annotateSelection(self, kind):
        if not self.canAnnotate: return
        if self._text_page < 0 or self._text_start == self._text_end:
            self.set_status('먼저 주석을 남길 글자를 드래그해 선택하세요.')
            return
        self.edit('add_markup', {'page':self._text_page, 'start':self._text_start, 'end':self._text_end,
            'kind':kind, 'author':self.annotationAuthor, 'color':self.annotationColor})

    @Slot(int, float, float)
    def composeComment(self, page, x, y):
        if not self.canAnnotate or self._text_editor_open or self._annotation_editor_open: return
        self.openComments.emit()
        self.showAnnotationEditor.emit({'mode':'new', 'page':page, 'point':[x,y],
            'author':self.annotationAuthor, 'color':self.annotationColor, 'content':'',
            'session':self._state['session'], 'revision':self._state['revision']})

    @Slot(bool)
    def setAnnotationEditorVisible(self, visible):
        self._annotation_editor_open = visible
        if visible: self.auto_timer.stop()
        elif self.active: self.auto_timer.start()

    @Slot(str)
    def editSelectedAnnotation(self, mode):
        item = self.selectedAnnotation
        if not item or not item['editable'] or not self.canAnnotate: return
        self.showAnnotationEditor.emit(dict(item, mode=mode,
            content='' if mode=='reply' else item['content'],
            author=self.annotationAuthor if mode=='reply' else item['author']))

    @Slot('QVariantMap', str, str, str)
    def commitAnnotation(self, data, content, author, color):
        data = dict(data)
        if data.get('session') != self._state['session'] or data.get('revision') != self._state['revision']:
            self.showError.emit('문서가 바뀌었어요. 주석을 다시 선택해 주세요.')
            return
        if not self.canAnnotate: return
        if data['mode'] != 'edit': self.setAnnotationAuthor(author)
        if data['mode']=='new':
            op = 'add_comment'
            args = {'page':data['page'], 'point':data['point'], 'content':content,
                    'author':author, 'color':color}
        else:
            args = {'page':data['page'], 'identifier':data['id'], 'content':content, 'author':author,
                    'revision':data['revision']}
            if data['mode']=='edit': args['color']=color
            op = 'reply_annotation' if data['mode']=='reply' else 'update_annotation'
        self._busy = True
        self.stateChanged.emit()
        def done(state):
            self.update_state(state)
            self.set_status('주석을 적용했어요. Ctrl+S로 PDF를 저장하세요.')
            self.annotationCommitted.emit()
        # Keep the editor and typed draft open on failure.
        self.command(op, args, done, error_callback=self.failure)

    @Slot()
    def deleteSelectedAnnotation(self):
        item = self.selectedAnnotation
        if not item or not item['editable'] or not self.canAnnotate: return
        answer = QMessageBox.question(None, '주석 삭제', '이 주석과 연결된 답글을 삭제할까요? 실행 취소로 되돌릴 수 있어요.',
                                      QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if answer != QMessageBox.Yes: return
        self.edit('delete_annotation', {'page':item['page'], 'identifier':item['id'], 'revision':item['revision']})

    @Slot()
    def copySelection(self):
        from PySide6.QtGui import QGuiApplication
        if self._selected_text:
            QGuiApplication.clipboard().setText(self._selected_text)
            self.set_status("선택한 텍스트를 복사했어요.")

    @Slot('QVariantMap')
    def activateLink(self, link):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        link = dict(link)
        if link.get("kind") == "page":
            page = int(link.get("page", -1))
            if 0 <= page < self._state["count"]:
                point = link.get("point", [0, 0])
                self.navigateRequested.emit(page, float(point[0]), float(point[1]))
            else:
                self.set_status("이 링크의 대상 페이지를 찾을 수 없어요.")
        elif link.get("kind") == "uri":
            uri = link.get("uri", "")
            url = QUrl(uri, QUrl.StrictMode)
            if (not url.isValid() or any(ord(c) < 32 for c in uri) or
                    url.scheme().lower() not in ("https", "http", "mailto") or
                    (url.scheme().lower() in ("http", "https") and not url.host())):
                self.showError.emit("웹(http/https)과 이메일 링크만 열 수 있어요.")
                return
            if not QDesktopServices.openUrl(url):
                self.showError.emit("링크를 열지 못했어요. Windows의 기본 브라우저 설정을 확인해 주세요.")
        else:
            self.showError.emit("이 링크 형식은 아직 지원하지 않아요.")

    @Slot()
    def openDefaultAppsSettings(self):
        """Open the supported Windows UI; never rewrite a user's default."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        if os.name != "nt":
            self.showError.emit("기본 PDF 앱 설정은 Windows에서 사용할 수 있어요.")
            return
        # The generic URI works on both Windows 10 and 11, including versions
        # that do not yet support the per-application query parameters.
        if not QDesktopServices.openUrl(QUrl("ms-settings:defaultapps")):
            self.showError.emit("Windows 설정을 열지 못했어요. 시작 → 설정 → 앱 → 기본 앱에서 .pdf의 앱을 윤DF로 선택해 주세요.")

    @Slot()
    def printDocument(self):
        from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QAbstractPrintDialog
        from PySide6.QtWidgets import QDialog
        from .printing import selected_pages
        if self._busy or self._ocr_busy or not self._state.get("count"): return
        if not self._state.get("printable"):
            self.showError.emit("이 PDF는 인쇄 권한이 제한되어 있어요.")
            return
        self.auto_timer.stop()
        printer = QPrinter(QPrinter.HighResolution)
        printer.setDocName(self._state["name"])
        printer.setResolution(300 if self._state.get("printHighQuality") else 150)
        dialog = QPrintDialog(printer)
        dialog.setWindowTitle("윤DF · 인쇄")
        dialog.setMinMax(1, self._state["count"])
        dialog.setFromTo(1, self._state["count"])
        dialog.setOption(QAbstractPrintDialog.PrintPageRange, True)
        dialog.setOption(QAbstractPrintDialog.PrintSelection, bool(self._selection))
        dialog.setOption(QAbstractPrintDialog.PrintCurrentPage, True)
        if dialog.exec() == QDialog.Accepted:
            pages = selected_pages(printer, self._state["count"], self._page, self._selection)
            self.printWithPrinter(printer, pages)
        else:
            self.auto_timer.start()

    def printWithPrinter(self, printer, pages):
        """Also used by integration QA with QPrinter's PDF output backend."""
        from .printing import PrintJob
        if self._busy or self._ocr_busy or not self._state.get("printable") or not pages: return
        self.auto_timer.stop()
        self._busy = True
        self.stateChanged.emit()
        self._print_job = PrintJob(self, printer, pages)
        self._print_job.start()

    @Slot(result=str)
    def licenseText(self):
        import sys
        root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
        return (root / "LICENSE").read_text(encoding="utf-8")

    @Slot()
    def openLogFolder(self):
        from .diagnostics import log_folder
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        folder=log_folder();folder.mkdir(parents=True,exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    @Slot()
    def chooseFont(self):
        path, _ = QFileDialog.getOpenFileName(None, "사용할 글꼴 선택", "C:/Windows/Fonts" if os.name == "nt" else "", "글꼴 (*.ttf *.otf)")
        if path:
            if not any(f["key"] == path for f in self._font_options):
                self._font_options.append({"key":path, "label":Path(path).stem + " · 직접 선택"})
            self.setFontChoice(path)

    @Slot(str)
    def search(self, query, navigate=True, restore=None):
        self._query = query.strip()
        self._search_token += 1
        token = self._search_token
        self._search, self._hits = [], []
        self._hit_index = -1
        self._search_waiting = 0 if navigate else None
        self._search_busy = bool(self._query and self._state["count"])
        self.searchChanged.emit()
        if not self._search_busy: return
        def next_page(index):
            if self.closed or token != self._search_token: return
            if index >= self._state["count"]:
                self._search_busy = False
                self.searchChanged.emit()
                if self._hits and self._search_waiting is not None and self.active:
                    self.selectSearchHit(self._search_waiting % len(self._hits))
                if not self._hits: self.set_status("일치하는 검색 결과가 없어요.")
                return
            def got(result):
                if self.closed or token != self._search_token or result.get("stale"): return
                if result["rects"]:
                    offset = len(self._hits)
                    self._search.append({"page": index, "count": len(result["rects"]),
                                         "rects": result["rects"], "firstHit": offset})
                    self._hits.extend({"page": index, "rect": rect} for rect in result["rects"])
                    self.searchChanged.emit()
                    if restore and restore.get("page") == index:
                        closest = min(range(offset, len(self._hits)), key=lambda n:
                                      abs(self._hits[n]["rect"][1]-restore["rect"][1]) +
                                      abs(self._hits[n]["rect"][0]-restore["rect"][0]))
                        self._hit_index = closest
                        self.searchChanged.emit()
                    if self._search_waiting is not None and 0 <= self._search_waiting < len(self._hits) and self.active:
                        self.selectSearchHit(self._search_waiting)
                next_page(index+1)
            def error(message):
                if token == self._search_token and not self.closed:
                    self._search_busy = False
                    self.searchChanged.emit()
                    self.showError.emit(message)
            self.command("search_page", {"page": index, "query": self._query}, got,
                         priority=10, guarded=True, error_callback=error)
        next_page(0)

    @Slot(int)
    def selectSearchHit(self, index):
        if not 0 <= index < len(self._hits): return
        self._hit_index = index
        self._search_waiting = None
        hit = self._hits[index]
        self.searchChanged.emit()
        self.set_status(f"찾기 {index+1} / {len(self._hits)} · {hit['page']+1}페이지")
        self.navigateRequested.emit(hit["page"], hit["rect"][0], hit["rect"][1])

    @Slot(int)
    def nextSearchHit(self, direction=1):
        if not self._hits:
            self._search_waiting = 0 if direction > 0 else -1
            return
        if self._search_busy and ((direction > 0 and self._hit_index == len(self._hits)-1) or
                                  (direction < 0 and self._hit_index <= 0)):
            self._search_waiting = len(self._hits) if direction > 0 else -1
            return
        index = (self._hit_index + direction) % len(self._hits) if self._hit_index >= 0 else (0 if direction > 0 else len(self._hits)-1)
        self.selectSearchHit(index)

    @Slot(str, int)
    def findNext(self, query, direction=1):
        if query.strip() != self._query: self.search(query)
        else: self.nextSearchHit(direction)

    @Slot()
    def inspectOcr(self):
        self._languages = ocr_languages()
        self.ocrChanged.emit()

    @Slot(str, str)
    def startOcr(self, scope, language):
        if self._busy or self._ocr_busy or not self._state["count"]: return
        if not language:
            self.showError.emit("사용할 OCR 언어가 없어요. Tesseract와 언어 데이터를 설치해 주세요.")
            return
        data = self._text_layouts.get(self._page, {})
        if data: self._auto_attempted.add((self._state["session"], data.get("pageId")))
        pages = list(range(self._state["count"])) if scope == "all" else (self._selection or [self._page]) if scope == "selected" else [self._page]
        self._ocr_busy = True
        self._ocr_cancel_requested = False
        self._ocr_progress = "OCR 준비 중…"
        self.ocrChanged.emit()

        self.auto_timer.stop()
        def started(snapshot):
            self._ocr_snapshot = snapshot["path"]
            if self._ocr_cancel_requested:
                self.finish_ocr()
                self.set_status("OCR를 취소했어요.")
                return
            self.ocr_dir = tempfile.mkdtemp(prefix="bichaek-ocr-")
            self.ocr_events = self.ctx.Queue()
            self.ocr_cancel = self.ctx.Event()
            self.ocr_process = self.ctx.Process(target=ocr_main,
                args=(snapshot, pages, language, self.ocr_dir, self.ocr_events, self.ocr_cancel))
            self.ocr_process.start()
        def error(message):
            self.finish_ocr()
            self.showError.emit(message)
        self.command("ocr_snapshot", {}, started, error_callback=error)

    @Slot()
    def cancelOcr(self):
        self._ocr_cancel_requested = True
        if self.ocr_cancel:
            self.ocr_cancel.set()
            self._ocr_progress = "OCR 취소 중…"
            self.ocrChanged.emit()

    def poll_ocr(self):
        if not self.ocr_events: return
        for _ in range(10):
            try: msg = self.ocr_events.get_nowait()
            except queue.Empty: break
            if msg.get("cancelled"):
                self.finish_ocr()
                self.set_status("OCR를 취소했어요. 문서는 변경하지 않았어요.")
                return
            if "error" in msg:
                self.finish_ocr()
                self.showError.emit(msg["error"])
                return
            if "progress" in msg:
                self._ocr_progress = f'OCR {msg["progress"]} / {msg["total"]} · 기존 텍스트 {msg["skipped"]}쪽 건너뜀'
                self.ocrChanged.emit()
            if msg.get("done"):
                self._ocr_progress = "인식한 문자층을 문서에 추가하는 중…"
                self.ocrChanged.emit()
                def merged(result):
                    self.update_state(result)
                    count = len(msg["results"])
                    self.finish_ocr()
                    self.set_status(f"OCR 완료 · {count}페이지에 검색 가능한 문자층을 추가했어요. 저장해 주세요.")
                def failed(message):
                    self.finish_ocr()
                    self.showError.emit(message)
                self.command("merge_ocr", {k: msg[k] for k in ("results", "revision", "session")}, merged, error_callback=failed)
                self.ocr_events = None
                return

    def finish_ocr(self):
        if self.ocr_process:
            self.ocr_process.join(timeout=1)
        if self.ocr_dir: shutil.rmtree(self.ocr_dir, ignore_errors=True)
        if self._ocr_snapshot:
            self.command("release_snapshot", {"path": self._ocr_snapshot})
            self._ocr_snapshot = None
        self.ocr_events = self.ocr_process = self.ocr_dir = self.ocr_cancel = None
        self._ocr_busy = False
        self._ocr_cancel_requested = False
        self._ocr_progress = ""
        self.ocrChanged.emit()
        self.auto_timer.start()

    @Slot(result=bool)
    def mayClose(self):
        if self._busy:
            self.showError.emit("진행 중인 작업이 끝난 뒤 닫아 주세요.")
            return False
        if self._ocr_busy:
            self.showError.emit("OCR를 취소한 뒤 닫아 주세요.")
            return False
        return self.confirm_discard()

    def shutdown(self):
        if self.closed: return
        if not self.hub: self.stopping.set()
        self.closed = True
        self._live_editor.dispose()
        for font_id in self._qt_font_ids.values():
            if font_id >= 0: QFontDatabase.removeApplicationFont(font_id)
        self._qt_font_ids.clear()
        self._search_token += 1
        self._annotation_token += 1
        self._render_queue.clear()
        self.images.clear_session(self._state.get("session"))
        self.auto_timer.stop()
        if self.merge_cancel:self.merge_cancel.set()
        if self.merge_process:
            self.merge_process.join(timeout=4)
            if self.merge_process.is_alive():self.merge_process.terminate();self.merge_process.join(timeout=2)
        if self._merge_temp:Path(self._merge_temp).unlink(missing_ok=True)
        if self._print_job: self._print_job.cancel()
        self.timer.stop()
        if self.ocr_cancel: self.ocr_cancel.set()
        if self.ocr_process:
            self.ocr_process.join(timeout=6)
            if self.ocr_process.is_alive(): self.ocr_process.terminate()
        if self.hub:
            self.hub.command(self, "close_document", priority=-5)
        else:
            self.inbox.put({"id": 0, "op": "quit", "priority": -100})
            self.process.join(timeout=4)
            if self.process.is_alive():
                self.process.terminate();self.process.join(timeout=2)
            self.frames.close()
        if self.ocr_dir: shutil.rmtree(self.ocr_dir, ignore_errors=True)
