"""Assemble a Windows runtime using CPython embed and official Windows wheels.
Run from any OS: python packaging/assemble_windows.py DOWNLOADS OUTPUT
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import shutil
import sys
import zipfile

root = Path(__file__).resolve().parent.parent
downloads, payload = map(lambda p: Path(p).resolve(), sys.argv[1:])
payload.mkdir(parents=True, exist_ok=True)
runtime = payload / 'runtime'
runtime.mkdir(exist_ok=True)
with zipfile.ZipFile(downloads / 'python-3.12.10-embed-amd64.zip') as z:
    z.extractall(runtime)
packages = runtime / 'packages'
packages.mkdir(exist_ok=True)
for pattern in ['PySide6_Essentials-6.8.3-*.whl', 'shiboken6-6.8.3-*.whl', 'pymupdf-1.26.6-*.whl', 'fonttools-4.61.1-py3-none-any.whl']:
    wheel, = downloads.glob(pattern)
    with zipfile.ZipFile(wheel) as z:
        z.extractall(packages)
(runtime / 'python312._pth').write_text('python312.zip\n.\npackages\n..\nimport site\n')
# Python loads native extensions before Qt's DLL search setup. Make the
# Microsoft runtime libraries available beside the interpreter as well.
for dll in (packages / 'PySide6').glob('*.dll'):
    if dll.name.lower().startswith(('msvcp', 'vcruntime', 'concrt')):
        shutil.copy2(dll, runtime / dll.name)
for name in ['bichaek', 'ui', 'assets', 'tessdata']:
    shutil.copytree(root / name, payload / name, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
for name in ['main.py', 'LICENSE', 'README.md', 'THIRD_PARTY_NOTICES.md']:
    shutil.copy2(root / name, payload / name)
source = payload / 'source'
shutil.copytree(root, source, dirs_exist_ok=True, ignore=shutil.ignore_patterns(
    '__pycache__', '*.pyc', '.venv', '.build-venv', 'build', 'dist',
    'test-output', 'tessdata', '.git', '.pytest_cache'))
licenses = payload / 'licenses'
licenses.mkdir(exist_ok=True)
for p in (downloads / 'licenses').glob('*'):
    shutil.copy2(p, licenses / p.name)
print('Payload:', payload)
print('Size:', sum(p.stat().st_size for p in payload.rglob('*') if p.is_file()))
