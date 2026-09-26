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
