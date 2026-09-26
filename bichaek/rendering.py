"""Bounded image cache and reusable GUI-owned shared frames.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from collections import OrderedDict
from multiprocessing import shared_memory
from threading import RLock
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider


class Images(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)
        self.images = OrderedDict()
        self.bytes = 0
        self.budget = 512 * 1024 * 1024
        self.thumb_budget = 64 * 1024 * 1024
        self.lock = RLock()

    def get(self, key):
        with self.lock:
            image = self.images.get(key)
            if image is not None: self.images.move_to_end(key)
            return image

    def put(self, key, value):
        image = value if isinstance(value, QImage) else QImage.fromData(value, 'PNG')
        with self.lock:
            if key in self.images: self.bytes -= self.images.pop(key).sizeInBytes()
            self.images[key] = image
            self.bytes += image.sizeInBytes()
            self.trim()

    def trim(self):
        with self.lock:
            # Thumbnails get their own allowance: zooming a large page must not
            # evict all sidebar previews. Keep one oversized frame if necessary.
            for thumb, budget in [(False,self.budget),(True,self.thumb_budget)]:
                keys = [k for k in self.images if ('-thumb-' in k) == thumb]
                total = sum(self.images[k].sizeInBytes() for k in keys)
                for key in keys[:-1]:
                    if total <= budget: break
                    size = self.images.pop(key).sizeInBytes()
                    self.bytes -= size; total -= size

    def clear(self):
        with self.lock:
            self.images = OrderedDict((k,v) for k,v in self.images.items() if k.startswith("merge-thumb-"))
            self.bytes = sum(v.sizeInBytes() for v in self.images.values())

    def clear_session(self, session):
        if not session: return
        with self.lock:
            for key in list(self.images):
                if key.startswith(session + "-"):
                    self.bytes -= self.images.pop(key).sizeInBytes()

    def requestImage(self, identifier, size, requestedSize):
        image = self.get(identifier)
        if image is None:
            image = QImage(1,1,QImage.Format_RGB32);image.fill(Qt.white)
        size.setWidth(image.width());size.setHeight(image.height())
        return image


class FramePool:
    """The GUI owns mappings until shutdown (required on Windows).

    A worker attaches, fills the mapping, closes its handle and returns only
    metadata. The GUI copies into its bounded cache before reusing the slot.
    Each slot handles the engine's 16-megapixel RGB limit. Allocation is lazy.
    """
    CAPACITY = 48_000_000 + 65536
    def __init__(self):
        self.frames = [None,None]
        self.busy = set()
        self.disabled = False
    def acquire(self):
        for index in range(len(self.frames)):
            if index in self.busy: continue
            if self.frames[index] is None and not self.disabled:
                try: self.frames[index] = shared_memory.SharedMemory(create=True,size=self.CAPACITY)
                except (OSError,MemoryError): self.disabled = True
            self.busy.add(index)
            return index,self.frames[index]
        return None
    def image(self,index,result):
        if 'png' in result: return QImage.fromData(result['png'],'PNG')
        frame=self.frames[index]
        return QImage(frame.buf,result['width'],result['height'],result['stride'],QImage.Format_RGB888).copy()
    def release(self,index):self.busy.discard(index)
    def close(self):
        for frame in self.frames:
            if frame:
                frame.close()
                try:frame.unlink()
                except FileNotFoundError:pass
        self.frames=[None,None];self.busy.clear()
