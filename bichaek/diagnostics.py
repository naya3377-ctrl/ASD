"""Local, bounded failure log; never uploads documents or diagnostics.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import logging, logging.handlers, os, sys, faulthandler

_native_log=None

def log_folder():
    return Path(os.environ.get('LOCALAPPDATA', Path.home()/'.local/share'))/'YoonDF'/'logs'

def install():
    global _native_log
    logger=logging.getLogger('yoondf')
    if logger.handlers:return
    try:
        folder=log_folder();folder.mkdir(parents=True,exist_ok=True)
        handler=logging.handlers.RotatingFileHandler(folder/f'app-{os.getpid()}.log',maxBytes=1024*1024,backupCount=1,encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler);logger.setLevel(logging.INFO)
        # Retain only a small number of logs from earlier application processes.
        for old in sorted(folder.glob('app-*.log*'),key=lambda p:p.stat().st_mtime,reverse=True)[12:]:
            try:old.unlink()
            except OSError:pass
        def exception(kind,value,tb):logger.error('Unhandled application exception',exc_info=(kind,value,tb))
        sys.excepthook=exception
        # Python exceptions do not capture faults inside a PDF/font native DLL.
        _native_log=open(folder/f'native-{os.getpid()}.log','a',encoding='utf-8')
        faulthandler.enable(file=_native_log,all_threads=True)
        for old in sorted(folder.glob('native-*.log'),key=lambda p:p.stat().st_mtime,reverse=True)[12:]:
            try:old.unlink()
            except OSError:pass
    except OSError:pass

def failure(stage):logging.getLogger('yoondf').exception(stage)

def note(message,*args):logging.getLogger('yoondf').info(message,*args)


class StallWatch:
    """Records GUI freezes (not only crashes) in the local log.

    A Qt timer marks the GUI thread alive; a background thread checks the mark.
    When the GUI stops for longer than `limit` seconds, the Python stack of the
    GUI thread at that moment is written once, then the total freeze length when
    it ends. A stack inside app.exec() means the time went to Qt/QML/drawing."""
    def __init__(self,limit=1.0):
        import threading,time
        from PySide6.QtCore import QTimer
        self.limit=limit;self.alive=time.monotonic();self.gui=threading.get_ident()
        self.timer=QTimer();self.timer.setInterval(100);self.timer.timeout.connect(self._beat);self.timer.start()
        self.stop_flag=threading.Event()
        threading.Thread(target=self._watch,name='yoondf-stall-watch',daemon=True).start()
    def _beat(self):
        import time;self.alive=time.monotonic()
    def stop(self):
        self.stop_flag.set();self.timer.stop()
    def _watch(self):
        import time,traceback
        reported=None
        while not self.stop_flag.wait(.25):
            gap=time.monotonic()-self.alive
            if gap>self.limit and reported is None:
                frame=sys._current_frames().get(self.gui)
                stack=''.join(traceback.format_stack(frame)[-12:]) if frame else '(no Python frame)'
                logging.getLogger('yoondf').warning('GUI freeze over %.1fs; GUI thread is at:\n%s',self.limit,stack)
                reported=self.alive
            elif reported is not None and self.alive!=reported:
                logging.getLogger('yoondf').warning('GUI freeze ended after %.1fs',self.alive-reported)
                reported=None
