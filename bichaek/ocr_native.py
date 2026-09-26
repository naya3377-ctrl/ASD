"""A cancellable page OCR subprocess using MuPDF's bundled Tesseract engine.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import sys


def make_layer(image, output, language, tessdata, dpi):
    import fitz
    pixmap = fitz.Pixmap(image)
    pixmap.set_dpi(int(dpi), int(dpi))
    with fitz.open("pdf", pixmap.pdfocr_tobytes(language=language, tessdata=tessdata)) as layer:
        # Keep only the invisible, searchable text. The source page is never
        # replaced by a rasterized page or covered by this OCR image.
        for xref in {entry[0] for entry in layer[0].get_images()}:
            layer[0].delete_image(xref)
        layer.save(output, garbage=4, deflate=True)


if __name__ == "__main__":
    make_layer(*sys.argv[1:])
