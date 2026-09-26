# Cross-building the offline Windows installer

The installer uses official x64 Windows wheels and CPython's embeddable
runtime. It does not depend on Python already being installed on the target.
The application source remains editable in the installed directory.

Build tools: Python 3.12, ziglang 0.16.0, NSIS 3.09. On Windows, the existing
PyInstaller/Inno Setup workflow is an alternative, but that older workflow
requires a separate Tesseract installation; this cross-build bundles OCR.

1. Download `python-3.12.10-embed-amd64.zip` from python.org into DOWNLOADS.
2. Download Windows wheels:
   `python -m pip download --dest DOWNLOADS --platform win_amd64 --python-version 312 --implementation cp --abi cp312 --only-binary=:all: PySide6-Essentials==6.8.3 shiboken6==6.8.3 PyMuPDF==1.26.6 fonttools==4.61.1`
3. Put `eng.traineddata`, `kor.traineddata` and LICENSE from tessdata_fast commit
   `87416418657359cb625c412a48b6e1d6d41c29bd` in the project `tessdata/` folder.
4. Put Qt's LGPL-3.0-only.txt, GPL-3.0-only.txt and Qt-GPL-exception-1.0.txt
   from qtbase v6.8.3 in DOWNLOADS/licenses.
5. Run `python packaging/assemble_windows.py DOWNLOADS PAYLOAD`.
6. From packaging/, compile both the stable launcher and branded Python host:
   `python -m ziglang rc /fo launcher.res launcher.rc`
   `python -m ziglang cc -target x86_64-windows-gnu -O2 -municode -Wl,--subsystem,windows launcher.c launcher.res -o PAYLOAD/YoonDF.exe`
   `python -m ziglang cc -target x86_64-windows-gnu -O2 -municode -Wl,--subsystem,windows python_host.c launcher.res -lshell32 -o PAYLOAD/runtime/YoonDF.exe`
7. From packaging/, run NSIS with absolute paths:
   `makensis -DPAYLOAD=PAYLOAD -DOUTPUT=OUTPUT.exe windows-cross.nsi`

The build uses no signing certificate. Verify installation, launching, editing,
OCR, GPU rendering and uninstall on Windows before a public stable release.

## Upgrade layout (0.5.1+)

The NSIS installer reserves a new `versions/VERSION-N` directory using
`CreateDirectoryW`, including for a repair of the same version. It extracts the
entire payload there and only then switches `current.ini` using
`MoveFileExW(REPLACE_EXISTING | WRITE_THROUGH)` on the same volume. The stable
root launcher resolves this file; without it, it can still start the legacy
flat installation or a portable payload. Shortcuts keep the root launcher path.

Old release directories and the legacy runtime are deliberately preserved while
upgrading, so a running reader or engine can finish and save its documents.
There is no process-name kill, forced app shutdown, Defender change or reboot
requirement. Additional disk space is needed for each successful installation.
The uninstaller removes the package directories; close all app windows first.

Extraction cannot skip required files (`AllowSkipFiles off`). Before activation,
failures clean up only the newly reserved release and leave the old selection.
Launcher/uninstaller replacements are staged separately and checked; no live
entry-point file is deleted before its replacement. A named mutex serializes
new installers/uninstallers. Silent maintenance failures return a nonzero exit
code without an error dialog.

The legacy Inno/PyInstaller build is separate; its Restart Manager options now
cover `*.exe,*.dll,*.pyd`. The distributed offline EXE uses NSIS.

## Tests and remaining Windows checks

`python -m unittest discover -s tests -v` includes a portable C harness that
compiles the actual `launcher.c` with Win32 test doubles. It covers version
selection, a same-version repair directory, legacy layout, Korean/space paths,
multiple quoted PDF arguments, invalid/truncated selection files, missing
runtime files and process-launch failure. These doubles do not emulate Windows
DLL locks or execute the NSIS installer.

On a disposable Windows 10/11 VM, validate these before a stable release:

1. Keep 0.5.0 open with an unsaved PDF and install 0.5.1. Verify the open document
   remains editable, `_bz2.pyd` is not overwritten, and a new shortcut launch
   opens 0.5.1. Save the old document and close it normally.
2. Keep 0.5.1 open and install it again. Verify the new `VERSION-N` differs from
   the open process's directory and both documents can be saved.
3. Cancel during extraction. Verify `current.ini` still selects the previous
   release and the partially extracted release is not activated.
4. Deny replacement of `current.ini` with a temporary exclusive handle. A silent
   installer must fail; the previous selector and release must remain intact.
5. Launch a second installer while the first is open; it must exit without
   extracting or switching anything.
6. Check a clean installation, a Korean username/space in the install path,
   desktop/Start Menu shortcuts, multiple PDF arguments, and app removal after
   all app windows have been closed. Keep a PDF outside the install directory
   and check it is untouched.

Windows installer execution and these lock/upgrade scenarios have not yet been
run on a Windows machine. The Linux build and extraction checks are not a
substitute for this gate.


## YoonDF name transition (0.6.0)

The product, desktop/Start Menu shortcut and new launcher are named 윤DF /
YoonDF. The legacy NSIS InstallDir registry key, maintenance mutex, QSettings
namespace and Python module name remain stable to find existing installations
and preferences. Fresh installations default to Programs/YoonDF; upgrades keep
the previously registered location. Both root YoonDF.exe and the compatibility
BichaekPDF.exe dispatch through current.ini, preserving older pinned shortcuts.
New payloads use YoonDF.exe. The uninstaller removes both entry points and the
old/new shortcut names. Historical directories are retained during upgrades.

The alternate Inno/PyInstaller recipe uses YoonDF.spec and retains its AppId
and document ProgID. Verify the renamed shortcuts, repair, older pinned links
and the Installed Apps display name on Windows before a stable public release.


## PDF application registration (0.6.1)

The per-user NSIS installer registers Applications/YoonDF.exe with SupportedTypes,
YoonDF.PDF, .pdf/OpenWithProgids, YoonDF/Capabilities/FileAssociations,
RegisteredApplications and App Paths. Both the executable and "%1" are quoted;
all paths use the stable root YoonDF.exe so later version switches do not break
PDF associations. SHChangeNotify notifies Explorer after install and uninstall.
Only owned keys/values are removed, never the .pdf parent or UserChoice.
The optional finish-page checkbox and the in-app settings action launch
ms-settings:defaultapps, which supports both Windows 10 and 11. The user chooses
the default in Windows. Portable/source runs do not register associations.

Windows release verification still required: fresh install and an upgrade into
a path with spaces/Korean characters; Open with and Default apps candidate lists;
select YoonDF for .pdf and double-click a Unicode/spaced PDF; upgrade again and
verify the same association; uninstall and check unrelated PDF apps remain.
The Inno Setup alternative carries equivalent registration, plus its legacy
BichaekPDF.Document alias, but is not compiled in the cross-built release.

Microsoft references:
- https://learn.microsoft.com/en-us/windows/win32/shell/app-registration
- https://learn.microsoft.com/en-us/windows/apps/develop/launch/launch-default-apps-settings


## Existing-window tab handoff (0.6.2)

`bichaek/instance.py` runs before Qt/PDF imports. Windows elects a reader using a
per-user, Local-session kernel mutex. LocalAppData/YoonDF/launch-session-ID holds
atomic, bounded launch requests and short-lived receipts. Only the mutex owner
consumes requests; ownership never depends on a PID file or a time-based stale
lock guess. Windows releases an abandoned mutex after a crash. Linux development
uses flock. No socket or TCP listener is used. The standard embedded Python
_ctypes.pyd and libffi-8.dll are already included in the offline payload.

A later launcher grants foreground eligibility to the owner when Windows allows
it, then exits after acknowledgement without importing Qt or creating another PDF
worker. The reader restores its previous window state and uses Documents.openPaths
for new tabs / existing-tab activation. ExternalOpenQueue defers switching until
QML/native dialogs close, preserving drafts and in-progress edits. Launch requests
received during application-close confirmation retry until that finishes or is
cancelled. A non-responsive reader produces a visible error after 15 seconds.

For Windows acceptance: close all pre-0.6.2 windows after upgrade; open one PDF,
then double-click another, multi-select several PDFs, reopen a dirty document,
launch the shortcut, minimize/maximize, and repeat while editing a comment and in
slideshow mode. Confirm one reader window, saved state and original unsaved edits.
Also verify simultaneous first launches and recovery after a terminated reader.
The versioned installer and stable root file-association launcher are unchanged.

## Editor and view fixes (0.7.0)

No runtime dependency change: CPython 3.12.10 embedded, Qt/PySide6 Essentials
6.8.3 and PyMuPDF 1.26.6. The incremental tab model, installed-font discovery,
font validation, image extraction and facing-page layout are application source
changes. The 0.7.0 launcher was compiled with ziglang 0.16.0 and linked as an
x64 GUI executable. NSIS remains the offline installer. Source is included both
in the installer and in the separate source archive under AGPL-3.0-or-later.
The release check extracts the installer and compares every payload file, checks
NSIS CRC, verifies the PE version/subsystem, and compares archived/embedded source
against the tested checkout. A real Windows installation and GPU check are still
required before calling this a stable public release.


## Direct editing and placement (0.8.0)

Same pinned Python, Qt and MuPDF runtime as 0.7.0. Application-only additions:
InlineTextEditor.qml, ImageHandles.qml, and image_objects.py. Native image forms
and Text annotation rectangles are saved in the PDF; no proprietary sidecar is
needed. The 0.8.0 launcher is built with ziglang 0.16.0. ScrollInput.qml stays
byte-identical to the verified 0.5.0 source. Windows acceptance still needs a
real installation, native IME/font behavior, DPI/GPU, and Acrobat round-trip.


## Live font editing (0.9.0)

Adds the official fonttools 4.61.1 pure-Python wheel for font names, collection
face extraction and restoring Unicode cmaps in embedded subsets. Keep its
dist-info license with the package. QPdfWriter is supplied by existing QtGui;
no QtPdf or additional network service is required. PyInstaller explicitly
collects dynamic fontTools table and CFF modules. QTextDocument is owned by the
editor; surviving QML views are detached before the document is replaced.
The same live document draws the saved PDF text fragment, with no second
HTML layout. Windows native font/IME, DPI and GPU checks remain outstanding.


## Original layout retention (0.9.1)

Adds application-only text_geometry.py using existing Qt APIs. Runtime dependency
versions are unchanged. Font programs remain embedded in vector PDF text, and
fragment insertion crops at the actual fractional point size without stretching.
The 0.9.1 launcher is built with ziglang 0.16.0 and the installer with NSIS 3.09.


## Font recovery, closing and branded process (0.9.2)

`packaging/python_host.c` loads the unmodified, adjacent `python312.dll` and calls
Py_SetProgramName/Py_Main in runtime/YoonDF.exe. This makes the actual interpreter
process identifiable as YoonDF.exe; its VERSIONINFO FileDescription is 윤DF.
The stable launcher prefers it and retains pythonw.exe fallback for old selected
releases. Python's documented python312._pth configuration remains in effect.
All arguments, including multiprocessing -c and font subprocess -m, are retained.
The application also sets AppUserModelID before creating its Qt window. This is
separate from the process executable's name. A portable C test compiles the actual
host source with Win32/Python entry-point doubles; it does not execute Windows.

Font parsing uses a disposable subprocess with a 15-second limit. A 25-second
UI response watchdog terminates the waiting state, preserves the draft, and ignores
late replies. A shared shutdown event cancels and reaps an active font subprocess
before the PDF worker exits. The subprocess never owns the editable PDF. The local error logger
keeps bounded per-process files in LocalAppData/YoonDF/logs. The PyInstaller entry
point separately dispatches --yoondf-font-job after multiprocessing.freeze_support.

Verify a clean and upgraded Windows installation, actual Task Manager Processes
and Details labels, Korean IME composition, missing-glyph fallback, worker launches,
font timeout/retry, and editing-close apply/save/discard/cancel before stable release.
These native acceptance checks have not been performed in the Linux build workspace.


## Editing stability (0.9.4)

No dependency changes. The cross-build retains CPython 3.12.10, Qt/PySide 6.8.3,
PyMuPDF 1.26.6 and fontTools 4.61.1. Validate `scripts/qa_edit_performance.py`
with the existing UI regressions. It checks the attached TextArea's actual
document width after IME events, 40-line paragraph stability, repeated save,
and heartbeat latency. Native-fault logs use Python's built-in faulthandler.
The current build has no Windows runner; native IME/GPU/installer acceptance
remains outstanding. See docs/EDITING_FIXES_094.md.
