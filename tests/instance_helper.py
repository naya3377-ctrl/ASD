"""Subprocess harness for the production launch relay (no Qt/PDF imports)."""
from pathlib import Path
import json
import os
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bichaek.instance import InstanceRelay, pdf_paths


if __name__ == '__main__':
    folder, log, *paths = sys.argv[1:]
    relay = InstanceRelay(folder)
    try:
        primary = relay.start_or_forward(pdf_paths(paths), timeout=5)
        print('PRIMARY' if primary else 'FORWARDED', flush=True)
        assert not any(x.startswith(('PySide6', 'pymupdf', 'fitz')) for x in sys.modules)
        if primary:
            def receive(values):
                with open(log, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({'pid': os.getpid(), 'paths': values}, ensure_ascii=False) + '\n')
                return True
            while not (Path(folder) / 'stop').exists():
                relay.poll(receive)
                time.sleep(.01)
    finally:
        relay.close()
