"""Deliver launch requests when switching documents cannot disturb a dialog.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from collections import deque
from PySide6.QtCore import QObject, Property, Signal, QTimer, QMetaObject
from PySide6.QtGui import QWindow
from PySide6.QtWidgets import QApplication


class ExternalOpenQueue(QObject):
    pendingChanged = Signal()

    def __init__(self, documents, parent=None):
        super().__init__(parent)
        self.documents = documents
        self.window = None
        self.queue = deque()
        self.draining = False
        self.restore_visibility = QWindow.Windowed
        self.timer = QTimer(self)
        self.timer.setInterval(80)
        self.timer.timeout.connect(self.drain)

    @Property(bool, notify=pendingChanged)
    def pending(self):
        return self.draining or bool(self.queue)

    def attach(self, window):
        self.window = window
        self.visibility_changed(window.visibility())
        window.visibilityChanged.connect(self.visibility_changed)

    def visibility_changed(self, value):
        if value in (QWindow.Windowed, QWindow.Maximized, QWindow.FullScreen):
            self.restore_visibility = value

    def reveal(self):
        if not self.window:
            return
        if self.window.visibility() in (QWindow.Minimized, QWindow.Hidden):
            self.window.setVisibility(self.restore_visibility)
        self.window.raise_()
        self.window.requestActivate()
        modal = QApplication.activeModalWidget()
        if modal:
            modal.raise_()
            modal.activateWindow()

    def receive(self, paths):
        self.reveal()
        if self.documents.closing:
            return False
        if paths:
            self.queue.append(list(paths))
            self.pendingChanged.emit()
            self.timer.start()
            QTimer.singleShot(0, self.drain)
        return True

    def drain(self):
        if not self.queue:
            self.timer.stop()
            return
        if (not self.window or self.draining or self.documents.closing or
            QApplication.activeModalWidget() or QApplication.activePopupWidget() or
            not self.window.property('externalOpenReady')):
            return
        self.draining = True
        try:
            if self.window.property('presenting'):
                QMetaObject.invokeMethod(self.window, 'endPresentation')
            self.documents.openPaths(self.queue.popleft())
            self.reveal()
        finally:
            self.draining = False
            self.pendingChanged.emit()
            if not self.queue:
                self.timer.stop()
