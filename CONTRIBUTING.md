# Contributing

Contributions are welcome under AGPL-3.0-or-later.

Keep all PyMuPDF operations in the dedicated engine process. Qt's main thread must remain responsive.
Avoid remote document uploads, telemetry, or background network calls.

Before changing edit behavior, add a round-trip integration test: create a PDF, edit it, save it, reopen it,
and verify the document's actual content. For OCR, test original image preservation as well as text extraction.
Never replace a failed edit with a cosmetic white overlay.

Run `python -m unittest tests.test_document -v` and validate the QML UI.
Windows releases additionally need a clean Windows 10/11 launch, Korean filenames,
high-DPI rendering, text edits, OCR cancellation, and installation/uninstallation checks.

Near-term work: native Windows benchmarks, finer text selection, annotation editing,
image object replacement/movement, font preservation, and more robust handling of complex PDFs.
