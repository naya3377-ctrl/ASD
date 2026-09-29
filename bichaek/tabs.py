"""Independent documents, one serialized PDF engine and one bounded frame pool.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import multiprocessing as mp
import os
import queue
import time

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer, QUrl, QAbstractListModel, QModelIndex, Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox

from .bridge import Bridge
from .rendering import FramePool
from .worker import engine_main


class EngineHub(QObject):
    def __init__(self):
        super().__init__()
        self.ctx = mp.get_context("spawn")
        self.inbox, self.outbox = self.ctx.Queue(), self.ctx.Queue()
        self.stopping = self.ctx.Event()
        self.process = self.ctx.Process(target=engine_main, args=(self.inbox, self.outbox, self.stopping), daemon=True)
        self.process.start()
        self.frames = FramePool()
        self.controllers = []
        self.retired = []
        self.callbacks = {}
        self.serial = 0
        self.failed = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(20)

    def command(self, owner, op, args=None, callback=None, priority=0, guarded=False, error_callback=None):
        if self.failed:
            if op not in ('close_document','quit'):
                message='PDF 처리기가 종료됐어요. 입력 중인 글을 복사해 보관한 뒤 윤DF를 다시 열어 주세요.'
                QTimer.singleShot(0,lambda:(error_callback or owner.failure)(message) if not owner.closed else None)
            return
        self.serial += 1
        self.callbacks[self.serial] = (owner, callback, error_callback)
        msg = {"id": self.serial, "document": owner.document_id, "op": op,
               "args": args or {}, "priority": priority}
        if guarded: msg.update(session=owner.document["session"], revision=owner.document["revision"])
        self.inbox.put(msg)

    def poll(self):
        # A time budget keeps each tick short; the rest waits for the next one.
        deadline = time.monotonic() + .008
        for _ in range(60):
            if time.monotonic() > deadline: break
            try: msg = self.outbox.get_nowait()
            except (queue.Empty, EOFError, OSError): break
            owner, success, error = self.callbacks.pop(msg["id"], (None, None, None))
            if owner is None: continue
            # Callbacks still run for a closed tab so outstanding shared frames
            # are released. Document callbacks independently reject stale work.
            if "error" in msg:
                if error: error(msg["error"])
                elif not owner.closed: owner.showError.emit(msg["error"])
            elif success: success(msg.get("result", {}))
        for owner in tuple(self.controllers):
            if not owner.closed:
                owner.poll_ocr()
                owner.poll_merge()
        if not self.failed and self.process.exitcode is not None:
            self.failed=True
            message='PDF 처리기가 예기치 않게 종료됐어요. 입력 중인 글은 유지했어요. 복사해 보관한 뒤 윤DF를 다시 열어 주세요.'
            callbacks=list(self.callbacks.values());self.callbacks.clear()
            for owner,success,error in callbacks:
                if owner.closed:continue
                if error:error(message)
            for owner in tuple(self.controllers):
                if not owner.closed:
                    owner._busy=False;owner._render_queue.clear();owner.stateChanged.emit()
                    owner.liveEditor.generation+=1;owner.liveEditor.timer.stop();owner.liveEditor.resume.stop();owner.liveEditor._pending_font=None
                    owner.liveEditor._fail(message)
                    owner.set_status(message)
            if self.controllers:self.controllers[0].showError.emit(message)
        owners = {entry[0] for entry in self.callbacks.values()}
        for owner in self.retired[:]:
            if owner not in owners:
                self.retired.remove(owner)
                owner.deleteLater()
        self.pump()

    def pump(self):
        if self.failed:return
        for owner in self.controllers:
            if owner.active and not owner.closed: owner._pump_render()

    def shutdown(self):
        self.timer.stop()
        self.stopping.set()
        for owner in tuple(self.controllers): owner.shutdown()
        self.inbox.put({"id": 0, "op": "quit", "priority": -100})
        self.process.join(timeout=4)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=2)
        self.frames.close()
        self.callbacks.clear()
        # A dead worker cannot drain its input pipe. Do not wait forever for
        # the queue's feeder to flush abandoned messages during app exit.
        self.inbox.cancel_join_thread()
        self.inbox.close()
        self.outbox.close()


class DocumentTabModel(QAbstractListModel):
    """Keep delegates alive while titles, busy flags and dirty state change."""
    Role = Qt.UserRole + 1

    def __init__(self, workspace):
        super().__init__(workspace)
        self.workspace = workspace

    def roleNames(self): return {self.Role: b"modelData"}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.workspace._tabs)

    def data(self, index, role):
        if role == self.Role and index.isValid() and 0 <= index.row() < self.rowCount():
            return self.workspace.tab_data(self.workspace._tabs[index.row()])

    def changed(self, owner):
        if owner in self.workspace._tabs:
            index = self.index(self.workspace._tabs.index(owner), 0)
            self.dataChanged.emit(index, index, [self.Role])


class Documents(QObject):
    tabsChanged = Signal()
    activeChanged = Signal()
    indexChanged = Signal()
    aboutToSwitch = Signal()
    closingChanged = Signal()
    closeApproved = Signal()
    showError = Signal(str)

    def __init__(self, images, library=None):
        super().__init__()
        self.images = images
        self.library = library
        self.hub = EngineHub()
        self._tabs = []
        self._tab_model = DocumentTabModel(self)
        self._index = -1
        self._closing = False
        self._close_approved = False
        self._close_all = []
        self._close_queue = []
        self.newTab()

    @Property(QObject, notify=activeChanged)
    def activeBridge(self): return self._tabs[self._index]

    @Property(int, notify=indexChanged)
    def activeIndex(self): return self._index

    @Property(bool, notify=closingChanged)
    def closing(self): return self._closing

    @Property(QObject, constant=True)
    def tabModel(self): return self._tab_model

    @staticmethod
    def tab_data(b):
        return {"id": b.document_id, "name": b.document.get("name") if b.document["count"] else
                (Path(b.opening_path).name if getattr(b, "opening_path", "") else "새 문서"),
                "path": b.document.get("path", getattr(b, "opening_path", "")),
                "dirty": b.document.get("dirty", False), "busy": b.busy or b.ocrBusy}

    @Slot(str)
    def openRecent(self, path):
        if not Path(path).is_file():
            if self.library: self.library.forget(path)
            self.showError.emit("파일을 찾지 못했어요. 옮겨졌거나 삭제되었을 수 있어요.\n" + path)
            return
        self.openPaths([path])

    @Property('QVariantList', notify=tabsChanged)
    def tabs(self): return [self.tab_data(b) for b in self._tabs]

    @Slot(str)
    def activateId(self, identifier):
        for index, b in enumerate(self._tabs):
            if b.document_id == identifier:
                self.activate(index)
                break

    @Slot(str)
    def closeId(self, identifier):
        for index, b in enumerate(self._tabs):
            if b.document_id == identifier:
                self.closeTab(index)
                break

    @Slot()
    def newTab(self):
        if self._closing: return
        b = Bridge(self.images, self.hub)
        b.workspace = self
        b.stateChanged.connect(lambda owner=b: self._document_changed(owner))
        b.ocrChanged.connect(lambda owner=b: self._document_changed(owner))
        b.showError.connect(lambda message, owner=b: self.showError.emit(
            (owner.document.get("name", "PDF") + ": " + message) if owner is not self.activeBridge else message))
        self._tab_model.beginInsertRows(QModelIndex(), len(self._tabs), len(self._tabs))
        self._tabs.append(b)
        self._tab_model.endInsertRows()
        self.hub.controllers.append(b)
        self.tabsChanged.emit()
        self.activate(len(self._tabs)-1)

    def _document_changed(self, owner):
        if not owner.busy and not owner.document["count"]:
            owner.opening_path = ""
        self._tab_model.changed(owner)
        self.tabsChanged.emit()

    @Slot(int)
    def activate(self, index):
        if not 0 <= index < len(self._tabs) or index == self._index: return
        self.aboutToSwitch.emit()
        if self._index >= 0: self.activeBridge.set_active(False)
        self._index = index
        b = self.activeBridge
        b.set_active(True)
        b.command("activate_document", priority=-2)
        self.activeChanged.emit()
        self.indexChanged.emit()

    @Slot(int, int)
    def moveTab(self, source, target):
        """Drag a tab to a new position. The active document stays active."""
        count = len(self._tabs)
        if self._closing or not (0 <= source < count and 0 <= target < count) or source == target: return
        # beginMoveRows wants the destination as an insert-before index.
        if not self._tab_model.beginMoveRows(QModelIndex(), source, source, QModelIndex(), target + 1 if target > source else target):
            return
        active = self._tabs[self._index] if self._index >= 0 else None
        self._tabs.insert(target, self._tabs.pop(source))
        self._tab_model.endMoveRows()
        if active is not None and self._tabs.index(active) != self._index:
            self._index = self._tabs.index(active)
            self.indexChanged.emit()
        self.tabsChanged.emit()

    @Slot(int)
    def cycle(self, direction):
        if not self._closing: self.activate((self._index + direction) % len(self._tabs))

    @Slot('QVariantMap')
    def rememberView(self, state):
        if self._index >= 0: self.activeBridge.view_state = dict(state)

    @Property('QVariantMap', notify=activeChanged)
    def viewState(self): return self.activeBridge.view_state

    @staticmethod
    def canonical(path):
        return os.path.normcase(str(Path(path).expanduser().resolve()))

    def other_open(self, path, owner):
        key = self.canonical(path)
        return next((b for b in self._tabs if b is not owner and
                     (b.document.get("path") or getattr(b, "opening_path", "")) and
                     self.canonical(b.document.get("path") or b.opening_path) == key), None)

    @Slot()
    def chooseOpen(self):
        paths, _ = QFileDialog.getOpenFileNames(None, "PDF를 새 탭으로 열기", "", "PDF 문서 (*.pdf)")
        self.openPaths(paths)

    @Slot('QVariantList')
    def openPaths(self, paths):
        if self._closing: return
        for value in paths:
            path = value.toLocalFile() if isinstance(value, QUrl) else str(value)
            if path.startswith("file:"): path = QUrl(path).toLocalFile()
            if not path: continue
            existing = self.other_open(path, None)
            if existing:
                self.activate(self._tabs.index(existing))
                continue
            if self.activeBridge.document["count"] or self.activeBridge.busy:
                self.newTab()
            b = self.activeBridge
            b.opening_path = path
            b.open_current(path)
            self.tabsChanged.emit()

    def ask_close(self, b):
        if b.busy or b.ocrBusy:
            self.showError.emit(b.document.get("name", "PDF") + "의 작업을 완료하거나 취소한 뒤 닫아 주세요.")
            return QMessageBox.Cancel
        if not b.document.get("dirty"): return QMessageBox.Discard
        return QMessageBox.question(None, "변경 사항 저장", b.document["name"] + "의 변경 사항을 저장할까요?",
                                   QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)

    def save_before_close(self, b, done, failed):
        b._busy = True
        b.stateChanged.emit()
        def saved(state):
            b.update_state(state)
            done()
        def error(message):
            b.failure(message)
            failed()
        b.command("save", {"path": b.document["path"]}, saved, error_callback=error)

    @Slot(int)
    def closeTab(self, index):
        if self._closing or not 0 <= index < len(self._tabs): return
        b = self._tabs[index]
        choice = self.ask_close(b)
        if choice == QMessageBox.Cancel: return
        if choice == QMessageBox.Save:
            self.save_before_close(b, lambda: self._remove(b), lambda: None)
        else: self._remove(b)

    @Slot()
    def closeAll(self):
        """Close every tab but keep the window, asking about each unsaved one.
        Cancel (or a failed save) stops with the remaining tabs left open."""
        if self._closing: return
        self._close_all = list(self._tabs)
        self._close_all_next()

    def _close_all_next(self):
        while self._close_all:
            b = self._close_all.pop(0)
            if b not in self._tabs: continue
            choice = self.ask_close(b)
            if choice == QMessageBox.Cancel:
                self._close_all = []; return
            if choice == QMessageBox.Save:
                def saved(b=b): self._remove(b); self._close_all_next()
                def failed(): self._close_all = []
                self.save_before_close(b, saved, failed)
                return
            self._remove(b)

    def _remove(self, b):
        if b not in self._tabs: return
        index = self._tabs.index(b)
        active = b is self.activeBridge
        if active: self.aboutToSwitch.emit()
        b.set_active(False)
        b.shutdown()
        self.hub.controllers.remove(b)
        b.stateChanged.disconnect()
        b.ocrChanged.disconnect()
        b.showError.disconnect()
        self.hub.retired.append(b)
        self._tab_model.beginRemoveRows(QModelIndex(), index, index)
        self._tabs.remove(b)
        self._tab_model.endRemoveRows()
        if not self._tabs:
            self._index = -1
            self.newTab()
        elif active:
            self._index = min(index, len(self._tabs)-1)
            self.activeBridge.set_active(True)
            self.activeBridge.command("activate_document", priority=-2)
            self.activeChanged.emit()
            self.indexChanged.emit()
        elif index < self._index:
            self._index -= 1
            self.indexChanged.emit()
        self.tabsChanged.emit()

    @Slot(result=bool)
    def mayClose(self):
        if self._close_approved: return True
        if self._closing: return False
        if any(b.busy or b.ocrBusy for b in self._tabs):
            self.showError.emit("진행 중인 작업을 완료하거나 취소한 뒤 닫아 주세요.")
            return False
        if not any(b.document.get("dirty") for b in self._tabs): return True
        self._closing = True
        self.closingChanged.emit()
        for b in self._tabs: b.auto_timer.stop()
        self._close_queue = list(self._tabs)
        QTimer.singleShot(0, self._close_next)
        return False

    def _cancel_close(self):
        self._closing = False
        self._close_queue.clear()
        self.closingChanged.emit()
        self.activeBridge.auto_timer.start()

    def _close_next(self):
        if not self._close_queue:
            self._close_approved = True
            self.closeApproved.emit()
            return
        b = self._close_queue.pop(0)
        choice = self.ask_close(b)
        if choice == QMessageBox.Cancel: self._cancel_close()
        elif choice == QMessageBox.Save:
            self.save_before_close(b, self._close_next, self._cancel_close)
        else: QTimer.singleShot(0, self._close_next)

    def shutdown(self): self.hub.shutdown()
