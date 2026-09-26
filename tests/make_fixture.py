"""Self-created, redistribution-safe sample. SPDX-License-Identifier: AGPL-3.0-or-later"""
from pathlib import Path
import fitz


def create(path):
    pdf = fitz.open()
    p = pdf.new_page(width=595, height=842)
    p.draw_rect((0,0,595,12), color=None, fill=(.196,.412,.875))
    p.insert_text((48,68), "BICHAEK / SAMPLE 01", fontsize=10, color=(.32,.37,.45))
    p.insert_text((46,155), "A document", fontsize=43, fontname="hebo", color=(.13,.16,.22))
    p.insert_text((46,208), "you can change.", fontsize=43, fontname="hebo", color=(.13,.16,.22))
    p.insert_htmlbox((48,239,544,315), "<p>읽고, 고치고, 다시 펼치다.</p>", css="*{font-family:sans-serif;font-size:22pt;}body,p{margin:0;}")
    p.draw_rect((48,357,548,361), fill=(.196,.412,.875), color=None)
    p.insert_text((48,411), "01   EDIT THE TEXT", fontsize=12, fontname="hebo", color=(.196,.412,.875))
    p.insert_textbox((48,431,530,477), "Click a text block in Edit text mode.\nReplace these words and save a new PDF.", fontsize=14, color=(.26,.3,.38))
    p.insert_text((48,527), "02   REARRANGE THE PAGES", fontsize=12, fontname="hebo", color=(.196,.412,.875))
    p.insert_textbox((48,547,530,591), "Drag a thumbnail in the sidebar.\nYour page order is part of the saved document.", fontsize=14, color=(.26,.3,.38))
    p.insert_text((48,642), "03   MAKE SCANS SEARCHABLE", fontsize=12, fontname="hebo", color=(.196,.412,.875))
    p.insert_textbox((48,662,530,717), "The last page is an image-only scan.\nRun English OCR to add a searchable text layer.", fontsize=14, color=(.26,.3,.38))
    p.insert_text((48,801), "Sample document / 01", fontsize=10, color=(.5,.54,.6))
    p = pdf.new_page(width=595,height=842)
    p.insert_text((48,80), "SECOND PAGE", fontsize=30, fontname="hebo")
    p.insert_text((48,145), "Keep this page when testing undo and redo.", fontsize=16)
    p.insert_htmlbox((48,190,540,250), "한글 본문을 수정하고 저장한 뒤 다시 열어 보세요.", css="*{font-family:sans-serif;font-size:18pt;}")
    p.draw_rect((48,325,547,625), color=None, fill=(.9,.93,.98))
    p.draw_circle((297,475),100,color=(.196,.412,.875),fill=(.196,.412,.875))
    p.insert_text((48,800), "Sample document / 02", fontsize=10)
    p = pdf.new_page(width=842,height=595)
    p.insert_text((48,90), "LANDSCAPE PAGE", fontsize=32,fontname="hebo")
    p.insert_text((48,145), "Mixed page sizes should keep their proportions.",fontsize=16)
    p.insert_text((48,195), "ROTATE THIS PAGE",fontsize=18)
    scan = fitz.open(); s = scan.new_page(width=595,height=842)
    s.insert_text((45,120),"SCANNED ARCHIVE",fontsize=30,fontname="hebo")
    s.insert_textbox((45,165,550,540), "This page contains an image only.\n\nOptical character recognition adds searchable text.\n\nThe original image should remain unchanged.\n\nBichaek PDF offline OCR test.", fontsize=18)
    pix = s.get_pixmap(matrix=fitz.Matrix(2,2))
    p = pdf.new_page(width=595,height=842); p.insert_image(p.rect,stream=pix.tobytes("png"))
    pdf.set_toc([[1,"Start",1],[1,"Page editing",2],[1,"Landscape",3],[1,"Scanned page",4]])
    pdf.set_metadata({"title":"Bichaek PDF sample", "author":"Bichaek PDF contributors"})
    pdf.save(path,deflate=True)
    pdf.close();scan.close()


if __name__ == "__main__":
    root=Path(__file__).resolve().parent.parent
    (root/"samples").mkdir(exist_ok=True)
    create(root/"samples"/"sample.pdf")
