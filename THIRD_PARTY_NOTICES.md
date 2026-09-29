# Third-party notices

YoonDF application code: Copyright (C) 2026 YoonDF contributors.
Licensed under AGPL-3.0-or-later; see LICENSE.

The Windows installer includes unmodified CPython 3.12.10, PySide6-Essentials
6.8.3, Shiboken6 6.8.3 and PyMuPDF 1.26.6 official binaries, plus fontTools 4.61.1
pure Python package. Application
Python/QML source and build scripts are installed in source/. Libraries remain
separate and replaceable in runtime/packages/. The licenses directory contains
Qt license texts; distribution metadata and Python LICENSE.txt are preserved.

| Component | Version used in this source preview | License / upstream |
| --- | --- | --- |
| PyMuPDF / MuPDF | PyMuPDF 1.26.6; bundled MuPDF reported by the wheel | AGPL v3 / commercial dual license. This project uses the AGPL option. https://pymupdf.readthedocs.io/en/latest/about.html |
| PySide6 / Qt | 6.8.3 | LGPL v3 / GPL v3 / commercial options, depending on module. https://doc.qt.io/qtforpython-6/licenses.html |
| fontTools | 4.61.1 | MIT. https://github.com/fonttools/fonttools/tree/4.61.1 |
| Tesseract | Engine bundled by the MuPDF wheel | Apache-2.0. https://github.com/tesseract-ocr/tesseract |
| Tesseract language data | tessdata_fast, commit 87416418657359cb625c412a48b6e1d6d41c29bd | Upstream data repository licenses. https://github.com/tesseract-ocr/tessdata_fast |
| pypdf (development tests only) | 6.10.0 | BSD-3-Clause. https://pypdf.readthedocs.io/en/stable/meta/license.html |
| PyInstaller | 6.16.0, build tool only | GPL with bootloader exception. https://pyinstaller.org/en/stable/license.html |
| Python | 3.12.10, official embeddable distribution | PSF license. https://docs.python.org/3/license.html |

The sample PDF is created by this project. Its embedded fonts come from
MuPDF's built-in font resources; their upstream notices remain applicable.
Application icon SVG is original source code in this project.

When distributing a compiled binary, provide corresponding application source
and build scripts, include the license notices of the bundled runtime and
libraries, and honor the applicable Qt/MuPDF distribution requirements.
The generated installer is not a substitute for those source and notice files.
This source preview is not automatically published to a public repository.

## Exact upstream source locations

- CPython 3.12.10: https://www.python.org/ftp/python/3.12.10/Python-3.12.10.tar.xz
- PyMuPDF 1.26.6 source distribution, including its pinned MuPDF build source:
  https://pypi.org/project/PyMuPDF/1.26.6/#files
- Qt 6.8.3 complete source: https://download.qt.io/archive/qt/6.8/6.8.3/single/
- PySide/Shiboken 6.8.3 source: https://code.qt.io/cgit/pyside/pyside-setup.git/tag/?h=v6.8.3
- Tesseract language data (Apache-2.0), eng and kor, unmodified:
  https://github.com/tesseract-ocr/tessdata_fast/tree/87416418657359cb625c412a48b6e1d6d41c29bd
  The full data license is installed in tessdata/LICENSE.
- fontTools 4.61.1 source and MIT license: https://github.com/fonttools/fonttools/tree/4.61.1
  Its full license is preserved in runtime/packages/fonttools-4.61.1.dist-info/licenses/LICENSE.
- NSIS installer engine: zlib/libpng license. https://nsis.sourceforge.io/License
- Microsoft Visual C++ runtime DLLs accompany the official Qt/Python wheels;
  Microsoft runtime redistribution terms apply.

CPython and its bundled binaries are unchanged. The documented python312._pth
search path is configured for the application. A separate AGPL-3.0-or-later host
(packaging/python_host.c) invokes CPython inside runtime/YoonDF.exe; it does not
patch Python binaries. The application can be modified in place without a signing
key. This alpha installer is not code-signed.
