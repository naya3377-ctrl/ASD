"""Per-user/session launch relay, before importing Qt or starting a PDF worker.

A kernel lock elects one reader. Small atomic request files pass absolute PDF
paths to it, without a listening network port. The lock is released by the OS
on a crash; its lifetime, not an on-disk PID, determines ownership.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import hashlib
import json
import os
import time
import uuid

MAX_REQUEST = 1024 * 1024


def pdf_paths(arguments):
    return [os.path.abspath(os.path.expanduser(p)) for p in arguments
            if isinstance(p, str) and p.lower().endswith('.pdf') and '\0' not in p]


def instance_directory():
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        session = wintypes.DWORD()
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        kernel.ProcessIdToSessionId.restype = wintypes.BOOL
        if not kernel.ProcessIdToSessionId(os.getpid(), ctypes.byref(session)):
            raise ctypes.WinError(ctypes.get_last_error())
        base = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData/Local')))
        return base / 'YoonDF' / ('launch-session-' + str(session.value))
    base = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache')))
    return base / 'yoondf' / 'launch'


class OlderReaderRunning(RuntimeError):
    def __init__(self, version):
        from . import __version__
        shown = ('윤DF ' + version) if version else '이전 버전의 윤DF'
        super().__init__(shown + ' 창이 아직 열려 있어요.\n\n새로 설치한 윤DF ' + __version__ +
                         '을(를) 쓰려면 열려 있는 윤DF 창을 모두 저장하고 닫은 뒤 다시 실행해 주세요.')


class ProcessLock:
    def __init__(self, directory):
        self.owned = False
        self.handle = None
        self.fd = None
        if os.name == 'nt':
            import ctypes
            from ctypes import wintypes
            self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
            self.kernel.CreateMutexW.restype = wintypes.HANDLE
            self.kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            self.kernel.WaitForSingleObject.restype = wintypes.DWORD
            self.kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
            self.kernel.ReleaseMutex.restype = wintypes.BOOL
            self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            self.kernel.CloseHandle.restype = wintypes.BOOL
            key = hashlib.sha256(os.path.normcase(str(directory)).encode('utf-8')).hexdigest()[:32]
            self.handle = self.kernel.CreateMutexW(None, False, 'Local\\YoonDF.Reader.' + key)
            if not self.handle:
                raise ctypes.WinError(ctypes.get_last_error())
        else:
            self.fd = os.open(str(directory / 'owner.lock'), os.O_CREAT | os.O_RDWR, 0o600)

    def acquire(self):
        if self.owned:
            return True
        if os.name == 'nt':
            result = self.kernel.WaitForSingleObject(self.handle, 0)
            if result == 0xFFFFFFFF:
                import ctypes
                raise ctypes.WinError(ctypes.get_last_error())
            self.owned = result in (0, 0x80)  # Acquired or abandoned by a crashed process.
        else:
            import fcntl
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.owned = True
            except BlockingIOError:
                pass
        return self.owned

    def close(self):
        if self.handle is not None:
            if self.owned:
                self.kernel.ReleaseMutex(self.handle)
            self.kernel.CloseHandle(self.handle)
            self.handle = None
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        self.owned = False


class InstanceRelay:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory is not None else instance_directory()
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = ProcessLock(self.directory)
        self.accepting = True
        self.seen = set()
        self.foreground_pid = None

    @staticmethod
    def write_atomic(path, value):
        data = json.dumps(value, ensure_ascii=False).encode('utf-8')
        if len(data) > MAX_REQUEST:
            raise ValueError('한 번에 여는 파일이 너무 많아요. 나누어서 열어 주세요.')
        temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            with temp.open('xb') as f:
                f.write(data)
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)

    def allow_foreground(self):
        if os.name != 'nt':
            return
        try:
            owner = json.loads((self.directory / 'owner.json').read_text(encoding='utf-8'))
            pid = int(owner['pid'])
            if pid <= 0 or pid == self.foreground_pid:
                return
            import ctypes
            from ctypes import wintypes
            user = ctypes.WinDLL('user32', use_last_error=True)
            user.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
            user.AllowSetForegroundWindow.restype = wintypes.BOOL
            if user.AllowSetForegroundWindow(pid):
                self.foreground_pid = pid
        except (OSError, ValueError, KeyError, TypeError):
            pass  # The reader can still open the tab if Windows refuses focus.

    def running_version(self):
        """Version of the reader that owns the lock: '' if unknown, None if it
        predates version stamps (0.9.6 and earlier wrote only the pid)."""
        try:
            owner = json.loads((self.directory / 'owner.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return ''
        return owner.get('appVersion') if isinstance(owner, dict) else ''

    def start_or_forward(self, paths, timeout=15):
        from . import __version__
        if not self.lock.acquire():
            running = self.running_version()
            if running is None or (running and running != __version__):
                # Handing the file to an older window would silently keep the
                # old program on screen after an update.
                raise OlderReaderRunning(running)
        self.allow_foreground()
        request = self.directory / ('r-' + str(time.time_ns()) + '-' + uuid.uuid4().hex + '.json')
        ack = request.with_suffix('.ack')
        self.write_atomic(request, {'version': 1, 'paths': paths})
        deadline = time.monotonic() + timeout
        while True:
            if ack.exists():
                result = json.loads(ack.read_text(encoding='utf-8'))
                ack.unlink(missing_ok=True)
                if result.get('error'):
                    raise RuntimeError(result['error'])
                return False
            if self.lock.acquire():
                from . import __version__
                self.write_atomic(self.directory / 'owner.json', {'pid': os.getpid(), 'appVersion': __version__})
                self._clean_receipts()
                return True
            self.allow_foreground()
            if time.monotonic() >= deadline:
                # A request already accepted by the reader has an ACK. Pending
                # requests are removed so a failed launch cannot open much later.
                if ack.exists():
                    continue
                request.unlink(missing_ok=True)
                raise RuntimeError('실행 중인 윤DF가 응답하지 않거나 종료 확인 중이에요. 열려 있는 대화상자를 닫고 다시 열어 주세요.')
            time.sleep(.05)

    def _clean_receipts(self):
        cutoff = time.time() - 60
        for path in self.directory.glob('r-*.ack'):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
            except FileNotFoundError:
                pass

    def poll(self, receive):
        if not self.accepting or not self.lock.owned:
            return
        for request in sorted(self.directory.glob('r-*.json'))[:32]:
            try:
                if request.stat().st_size > MAX_REQUEST:
                    raise ValueError('요청이 너무 큽니다.')
                message = json.loads(request.read_text(encoding='utf-8'))
                paths = message.get('paths')
                if (message.get('version') != 1 or not isinstance(paths, list) or
                    len(paths) > 1024 or any(not isinstance(p, str) or '\0' in p or
                    not os.path.isabs(p) or not p.lower().endswith('.pdf') for p in paths)):
                    raise ValueError('올바른 PDF 열기 요청이 아닙니다.')
                if request.name not in self.seen:
                    if not receive(paths):
                        continue  # Closing: the launcher retries or takes over after exit.
                    self.seen.add(request.name)
                self.write_atomic(request.with_suffix('.ack'), {'accepted': True})
                request.unlink(missing_ok=True)
                self.seen.discard(request.name)
            except FileNotFoundError:
                pass  # A waiting launcher timed out and removed its request.
            except (ValueError, TypeError, AttributeError) as exc:
                self.write_atomic(request.with_suffix('.ack'), {'error': str(exc)})
                request.unlink(missing_ok=True)
        self._clean_receipts()

    def stop(self):
        self.accepting = False

    def close(self):
        self.stop()
        try:
            if self.lock.owned:
                (self.directory / 'owner.json').unlink(missing_ok=True)
        finally:
            self.lock.close()
