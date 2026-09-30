"""Recent documents and the last reading position of each file.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import json
import os
import time

from PySide6.QtCore import QObject, Property, Signal, Slot, QSettings, QTimer


class Library(QObject):
    """Small local history kept in QSettings. Nothing leaves the computer."""
    LIMIT = 12
    changed = Signal()

    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self.settings = settings or QSettings("Bichaek", "BichaekPDF")
        self._entries = self._load()
        self._flush = QTimer(self)
        self._flush.setSingleShot(True)
        self._flush.setInterval(1500)
        self._flush.timeout.connect(self.flush)

    @staticmethod
    def key(path):
        return os.path.normcase(str(Path(path).expanduser().resolve()))

    def _load(self):
        try:
            raw = json.loads(str(self.settings.value("recentFiles", "[]") or "[]"))
        except (TypeError, ValueError):
            return []
        entries = []
        for item in raw if isinstance(raw, list) else []:
            if isinstance(item, dict) and isinstance(item.get("path"), str) and item["path"]:
                entries.append({"path": item["path"], "name": str(item.get("name") or Path(item["path"]).name),
                                "page": max(0, int(item.get("page") or 0)),
                                "count": max(0, int(item.get("count") or 0)),
                                "opened": float(item.get("opened") or 0)})
        return entries[:self.LIMIT]

    @Property(bool, notify=changed)
    def enabled(self):
        return self.settings.value("rememberRecent", True, type=bool)

    @Slot(bool)
    def setEnabled(self, value):
        self.settings.setValue("rememberRecent", bool(value))
        if not value:
            self._entries = []
            self.flush()
        self.changed.emit()

    @Property('QVariantList', notify=changed)
    def recent(self):
        return [dict(e, exists=Path(e["path"]).is_file()) for e in self._entries]

    def _find(self, path):
        key = self.key(path)
        return next((e for e in self._entries if self.key(e["path"]) == key), None)

    def opened(self, path, name, count):
        """Record an opened file and return the page to resume from."""
        if not path or not self.enabled:
            return 0
        entry = self._find(path)
        page = entry["page"] if entry else 0
        if entry:
            self._entries.remove(entry)
        self._entries.insert(0, {"path": str(path), "name": name or Path(path).name,
                                 "page": page if 0 <= page < count else 0,
                                 "count": int(count), "opened": time.time()})
        del self._entries[self.LIMIT:]
        self.flush()
        return self._entries[0]["page"]

    def remember(self, path, page):
        entry = self._find(path) if path and self.enabled else None
        if entry and entry["page"] != page:
            entry["page"] = max(0, int(page))
            self._flush.start()

    @Slot(str)
    def forget(self, path):
        entry = self._find(path)
        if entry:
            self._entries.remove(entry)
            self.flush()

    @Slot()
    def clear(self):
        self._entries = []
        self.flush()

    @Slot()
    def flush(self):
        self._flush.stop()
        self.settings.setValue("recentFiles", json.dumps(self._entries, ensure_ascii=False))
        self.changed.emit()


_shared = None


def shared_library():
    global _shared
    if _shared is None:
        _shared = Library()
    return _shared
