"""Cancellable, one-page-at-a-time raster printing of the live PDF.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QImage, QPainter
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QProgressDialog


def selected_pages(printer, count, current, selection):
    mode = printer.printRange()
    if mode == QPrinter.PageRange:
        pages = list(range(max(0, printer.fromPage()-1), min(count, printer.toPage())))
    elif mode == QPrinter.Selection:
        pages = sorted(set(p for p in selection if 0 <= p < count))
    elif mode == QPrinter.CurrentPage:
        pages = [current]
    else:
        pages = list(range(count))
    if printer.pageOrder() == QPrinter.LastPageFirst:
        pages.reverse()
    # Hardware-supported copies are left to the spooler; never duplicate twice.
    if not printer.supportsMultipleCopies() and printer.copyCount() > 1:
        copies = printer.copyCount()
        pages = pages * copies if printer.collateCopies() else [p for p in pages for _ in range(copies)]
        printer.setCopyCount(1)
    return pages


class PrintJob:
    def __init__(self, bridge, printer, pages):
        self.bridge, self.printer, self.pages = bridge, printer, list(pages)
        self.index = 0
        self.finished = False
        self.painter = QPainter()
        self.progress = QProgressDialog("인쇄 준비 중…", "취소", 0, len(pages))
        self.progress.setWindowTitle("윤DF · 인쇄")
        self.progress.setWindowModality(Qt.ApplicationModal)
        self.progress.setMinimumDuration(0)
        self.progress.setAutoClose(False)
        self.progress.setAutoReset(False)
        self.progress.canceled.connect(self.cancel)

    def start(self):
        if not self.printer.isValid() or not self.painter.begin(self.printer):
            self.finish("프린터를 시작하지 못했어요. 프린터 연결과 설정을 확인해 주세요.")
            return
        self.progress.show()
        self.next_page()

    def next_page(self):
        if self.finished: return
        if self.index == len(self.pages):
            self.finish()
            return
        self.progress.setLabelText(f"{self.pages[self.index]+1}페이지 인쇄 중 · {self.index+1}/{len(self.pages)}")
        self.progress.setValue(self.index)
        self.bridge.set_status(self.progress.labelText())
        self.bridge.command("render_print", {"page": self.pages[self.index], "dpi": self.printer.resolution()},
                            self.paint, priority=1, guarded=True, error_callback=self.finish)

    def paint(self, result):
        if self.finished: return
        try:
            if result.get("stale"):
                raise RuntimeError("인쇄 중 문서가 변경되어 인쇄를 중단했어요.")
            image = QImage.fromData(result["png"], "PNG")
            if image.isNull(): raise RuntimeError("인쇄할 페이지를 만들지 못했어요.")
            if self.index and not self.printer.newPage():
                raise RuntimeError("프린터가 다음 페이지를 받지 못했어요.")
            # Non-full-page printer coordinates start at the printable origin.
            area = QRectF(self.painter.viewport())
            ratio = min(area.width()/image.width(), area.height()/image.height())
            w, h = image.width()*ratio, image.height()*ratio
            target = QRectF(area.x()+(area.width()-w)/2, area.y()+(area.height()-h)/2, w, h)
            self.painter.setRenderHint(QPainter.SmoothPixmapTransform)
            self.painter.drawImage(target, image)
            self.index += 1
            QTimer.singleShot(0, self.next_page)
        except Exception as exc:
            self.finish(str(exc))

    def cancel(self):
        self.finish(cancelled=True)

    def finish(self, error="", cancelled=False):
        if self.finished: return
        self.finished = True
        if error or cancelled: self.printer.abort()
        ended = self.painter.end() if self.painter.isActive() else False
        if not error and not cancelled and not ended:
            error = "인쇄 작업을 완료하지 못했어요. 프린터 상태를 확인해 주세요."
        self.progress.close()
        self.progress.deleteLater()
        self.bridge._print_job = None
        self.bridge._busy = False
        self.bridge.stateChanged.emit()
        self.bridge.auto_timer.start()
        self.bridge.set_status("인쇄를 취소했어요." if cancelled else "인쇄하지 못했어요." if error else "인쇄 작업을 프린터로 보냈어요.")
        if error: self.bridge.showError.emit(error)
