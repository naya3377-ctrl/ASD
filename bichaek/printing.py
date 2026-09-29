"""Cancellable, one-page-at-a-time raster printing of the live PDF, and the
page placement shared by the print preview and the printer.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import re
from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QImage, QPainter, QTransform
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QProgressDialog


def parse_range(text, count):
    """'1-3, 5, 8-' → [0, 1, 2, 4, 7, 8, …] (0-based, in the order written).
    Raises ValueError with a message for the user."""
    pages = []
    for part in re.split(r"[,\s]+", str(text).strip()):
        if not part: continue
        m = re.fullmatch(r"(\d*)\s*[-~]\s*(\d*)|(\d+)", part)
        if not m or part in ("-", "~"):
            raise ValueError(f"페이지 범위를 읽을 수 없어요: {part}  (예: 1-3, 5)")
        if m.group(3):
            first = last = int(m.group(3))
        else:
            first = int(m.group(1) or 1); last = int(m.group(2) or count)
        if first < 1 or last < 1 or first > count or last > count:
            raise ValueError(f"1~{count} 사이의 페이지를 적어 주세요: {part}")
        step = 1 if last >= first else -1
        pages.extend(range(first - 1, last - 1 + step, step))
    if not pages:
        raise ValueError("인쇄할 페이지를 적어 주세요. (예: 1-3, 5)")
    return pages


def expand_copies(printer, pages):
    """Hardware-supported copies are left to the spooler; never duplicate twice."""
    if not printer.supportsMultipleCopies() and printer.copyCount() > 1:
        copies = printer.copyCount()
        pages = pages * copies if printer.collateCopies() else [p for p in pages for _ in range(copies)]
        printer.setCopyCount(1)
    return pages


def paper_orientation(sizes):
    """'landscape' when most selected pages are wider than tall."""
    wide = sum(1 for w, h in sizes if w > h)
    return "landscape" if wide * 2 > len(sizes) else "portrait"


def place(page_w, page_h, area, fit="fit", rotate=False):
    """Where a page lands on the sheet, in points: (x, y, w, h) inside the
    printable `area` (x, y, w, h). fit: 'fit' scales to the area, 'actual'
    keeps 100 %, 'shrink' only reduces pages that are too large. A rotated
    page is laid out turned by 90°."""
    if rotate: page_w, page_h = page_h, page_w
    ax, ay, aw, ah = area
    scale = min(aw / page_w, ah / page_h)
    if fit == "actual": scale = 1.0
    elif fit == "shrink": scale = min(1.0, scale)
    w, h = page_w * scale, page_h * scale
    return (ax + (aw - w) / 2, ay + (ah - h) / 2, w, h)


def needs_rotation(page_w, page_h, paper_w, paper_h, auto):
    """Auto orientation turns a page whose shape disagrees with the paper."""
    return bool(auto) and (page_w > page_h) != (paper_w > paper_h) and abs(page_w - page_h) > 1


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
    return expand_copies(printer, pages)


class PrintJob:
    """layout: {'fit': 'fit'|'actual'|'shrink', 'auto_rotate': bool, 'gray': bool}.
    Without it pages are fitted to the printable area as before."""
    def __init__(self, bridge, printer, pages, layout=None):
        self.bridge, self.printer, self.pages = bridge, printer, list(pages)
        self.layout = dict(layout or {})
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
            page_w, page_h = result.get("pageWidth") or image.width(), result.get("pageHeight") or image.height()
            paint = self.printer.pageLayout().paintRectPoints()
            rotate = needs_rotation(page_w, page_h, paint.width(), paint.height(), self.layout.get("auto_rotate"))
            if rotate: image = image.transformed(QTransform().rotate(90))
            if self.layout.get("gray"): image = image.convertToFormat(QImage.Format_Grayscale8)
            # The shared placement works in points; the device may use any resolution.
            unit = area.width() / max(1.0, paint.width())
            x, y, w, h = place(page_w, page_h, (0, 0, paint.width(), paint.height()), self.layout.get("fit", "fit"), rotate)
            target = QRectF(area.x() + x*unit, area.y() + y*unit, w*unit, h*unit)
            self.painter.setClipRect(area)
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
