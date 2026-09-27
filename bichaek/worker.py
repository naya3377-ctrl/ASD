"""Serialized PDF worker and independent cancellable OCR process.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import time
import traceback


def describe(exc):
    """MuPDF's own messages ("code=8: invalid key in dict") mean nothing to a
    reader. Say what happened in plain words and keep the detail for reports."""
    if type(exc).__name__.startswith("FzError"):
        return "PDF 내부 구조의 일부를 읽지 못해서 작업을 마치지 못했어요. (MuPDF: %s)" % exc
    return str(exc)


def engine_main(inbox, outbox, stopping=None):
    from .diagnostics import install, failure
    install()
    from . import font_jobs
    font_jobs.CANCEL_EVENT = stopping
    from .document import Document
    engines = {}
    closed = set()
    pending = []
    try:
        while True:
            if not pending:
                pending.append(inbox.get())
            while True:
                try:
                    pending.append(inbox.get_nowait())
                except queue.Empty:
                    break
            # User actions outrank prefetch and thumbnails. Stable sort preserves
            # the ordering of edits. All MuPDF access remains in this process.
            pending.sort(key=lambda x: x.get("priority", 0))
            msg = pending.pop(0)
            if msg["op"] == "quit":
                break
            try:
                key = msg.get("document", "default")
                if msg["op"] == "close_document":
                    old = engines.pop(key, None)
                    if old: old.close()
                    closed.add(key)
                    outbox.put({"id": msg["id"], "result": {}})
                    continue
                if key in closed:
                    outbox.put({"id": msg["id"], "result": {"stale": True}})
                    continue
                if key not in engines: engines[key] = Document()
                engine = engines[key]
                if msg["op"] == "activate_document":
                    for other in engines.values():
                        if other is not engine: other._display_lists.clear()
                    result = {}
                elif msg.get("session") and msg["session"] != engine.session:
                    result = {"stale": True}
                elif msg.get("revision") is not None and msg["revision"] != engine.revision:
                    result = {"stale": True}
                else:
                    started = time.monotonic()
                    result = getattr(engine, msg["op"])(**msg.get("args", {}))
                    spent = time.monotonic() - started
                    if spent > 1.0:
                        # Slow PDF work does not freeze the window but delays it.
                        from .diagnostics import note
                        note("slow PDF operation %s %.2fs (page %s)", msg["op"], spent, msg.get("args", {}).get("page", "-"))
                outbox.put({"id": msg["id"], "op": msg["op"], "result": result})
            except Exception as exc:
                failure('PDF operation: '+msg['op'])
                outbox.put({"id": msg["id"], "op": msg["op"], "error": describe(exc),
                            "trace": traceback.format_exc()})
    finally:
        for engine in engines.values(): engine.close()


def find_tesseract():
    found = shutil.which("tesseract")
    if found:
        return found
    for root in [os.environ.get("ProgramFiles", "C:/Program Files"),
                 os.environ.get("LOCALAPPDATA", "")]:
        for sub in ["Tesseract-OCR/tesseract.exe", "Programs/Tesseract-OCR/tesseract.exe"]:
            path = Path(root) / sub
            if path.is_file():
                return str(path)
    return ""


def bundled_tessdata():
    folder = Path(__file__).resolve().parent.parent / "tessdata"
    return folder if (folder / "eng.traineddata").is_file() else None


def ocr_languages():
    folder = bundled_tessdata()
    if folder:
        return sorted(p.stem for p in folder.glob("*.traineddata"))
    binary = find_tesseract()
    if not binary:
        return []
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        r = subprocess.run([binary, "--list-langs"], capture_output=True, text=True,
                           timeout=8, creationflags=flags)
        return [s.strip() for s in r.stdout.splitlines()[1:] if s.strip()]
    except Exception:
        return []


def ocr_main(snapshot, pages, language, directory, events, cancel):
    import fitz
    doc = None
    process = None
    try:
        tessdata = bundled_tessdata()
        binary = find_tesseract() if not tessdata else ""
        if not binary and not tessdata:
            raise RuntimeError("Tesseract OCR가 설치되어 있지 않아요. README의 OCR 설치 안내를 확인해 주세요.")
        available = ocr_languages()
        missing = [s for s in language.split("+") if s not in available]
        if missing:
            raise RuntimeError("OCR 언어 데이터가 없어요: " + ", ".join(missing))
        doc = fitz.open(snapshot["path"])
        if doc.needs_pass:
            doc.authenticate(snapshot["password"])
        outputs, skipped = [], 0
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        for progress, index in enumerate(pages):
            if cancel.is_set():
                events.put({"cancelled": True})
                return
            page = doc[index]
            if page.get_text().strip():
                skipped += 1
            else:
                page.set_rotation(0)
                # Bound image dimensions and memory while retaining useful OCR DPI.
                scale = min(200 / 72, 7000 / max(page.rect.width, page.rect.height))
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                img = Path(directory) / f"page-{index}.png"
                pix.save(img)
                stem = str(Path(directory) / f"ocr-{index}")
                log_path = Path(directory) / f"ocr-{index}.log"
                if tessdata:
                    command = [sys.executable, "-m", "bichaek.ocr_native", str(img),
                               stem + ".pdf", language, str(tessdata), str(round(scale * 72))]
                else:
                    command = [binary, str(img), stem, "-l", language,
                               "--dpi", str(round(scale * 72)), "-c", "textonly_pdf=1", "pdf"]
                with log_path.open("wb") as log:
                    process = subprocess.Popen(command,
                        stdout=log, stderr=log, creationflags=flags,
                        env={**os.environ, "OMP_THREAD_LIMIT": "2"})
                    start = time.monotonic()
                    while process.poll() is None:
                        if cancel.is_set() or time.monotonic() - start > 180:
                            process.terminate()
                            process.wait(timeout=5)
                            if cancel.is_set():
                                events.put({"cancelled": True})
                                return
                            raise RuntimeError(f"{index+1}페이지 OCR 시간이 초과됐어요.")
                        time.sleep(.08)
                if process.returncode:
                    raise RuntimeError(log_path.read_text(errors="replace")[-600:])
                process = None
                output = stem + ".pdf"
                with fitz.open(output) as layer:
                    if layer[0].get_text().strip():
                        outputs.append({"page": index, "path": output})
                img.unlink(missing_ok=True)
            events.put({"progress": progress+1, "total": len(pages), "skipped": skipped})
        events.put({"done": True, "results": outputs, "skipped": skipped,
                    "revision": snapshot["revision"], "session": snapshot["session"]})
    except Exception as exc:
        events.put({"error": str(exc)})
    finally:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        if doc:
            doc.close()
