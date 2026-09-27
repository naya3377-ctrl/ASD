"""Comments on 38 kinds of PDF: every comment action, then save and reopen.

Korean text; turned, cropped and shifted pages; damaged objects (unused,
referenced, in object streams, in the document info, in the comment list);
broken stream lengths and images; object and xref streams; incremental saves;
damaged cross-reference tables and stray bytes; AES/RC4 passwords and
permission mixes; links, forms, shared and indirect comment lists; foreign
comments with odd entries; inherited rotation; tagged PDFs; 300 pages; huge
and tiny pages. Each gets a note, four text marks, edit, reply, move, delete,
undo/redo, save, and an independent reopen. The hand-written damaged files
are also rendered before and after to show the page itself did not change.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import hashlib, os, re, shutil, sys, time, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import fitz
fitz.TOOLS.mupdf_display_errors(False)
from bichaek.document import Document

OUT = str(ROOT / "test-output" / "annotation-matrix")
import fitz
fitz.TOOLS.mupdf_display_errors(False)
from bichaek.document import Document

KO = "문화예술활동현황조사 통계정보보고서"

def page_text(p, y=140, ko=True):
    p.insert_text((72, y), "Alpha beta gamma delta", fontsize=18)
    if ko: p.insert_text((72, y+40), KO, fontsize=18, fontname="korea")

def plain(n=2, **kw):
    pdf = fitz.open()
    for i in range(n):
        p = pdf.new_page(width=595, height=842); page_text(p)
    return pdf

def save(pdf, name, **kw):
    path = f"{OUT}/{name}.pdf"; pdf.save(path, **kw); pdf.close(); return path

def patch(path, old, new, count=1):
    data = open(path, "rb").read(); assert old in data, (path, old)
    open(path, "wb").write(data.replace(old, new, count))

V = {}
def variant(fn): V[fn.__name__] = fn; return fn

@variant
def korean_simple(): return save(plain(), "korean_simple")
@variant
def rotated_cropped():
    pdf = fitz.open()
    for r in (0, 90, 180, 270):
        p = pdf.new_page(width=660, height=860); page_text(p)
        p.set_cropbox(fitz.Rect(30, 40, 630, 840)); p.set_rotation(r)
    return save(pdf, "rotated_cropped")
@variant
def mediabox_offset():
    path = save(plain(1), "mediabox_offset")
    d = fitz.open(path); x = d[0].xref
    d.xref_set_key(x, "MediaBox", "[-50 -60 545 782]"); d.saveIncr(); d.close(); return path
@variant
def broken_unused():
    pdf = plain(); x = pdf.get_new_xref(); pdf.update_object(x, "<< /A 1 >>")
    path = save(pdf, "broken_unused"); patch(path, b"<</A 1>>", b"<</A 1 (junk) 2>>"); return path
@variant
def broken_referenced_font():
    pdf = plain(); x = pdf.get_new_xref(); pdf.update_object(x, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /QQ 1 >>")
    pdf.xref_set_key(pdf[0].xref, "Resources/Font/FZZ", f"{x} 0 R") if False else None
    res = pdf.xref_get_key(pdf[0].xref, "Resources")
    path = save(pdf, "broken_referenced_font")
    d = fitz.open(path)
    # reference the object from page 1's resources (unused by content)
    r = d.xref_get_key(d[0].xref, "Resources")
    if r[0] == "xref":
        rx = int(r[1].split()[0]); d.xref_set_key(rx, "Font/FZZ", f"{x} 0 R")
    else:
        d.xref_set_key(d[0].xref, "Resources/Font/FZZ", f"{x} 0 R")
    d.save(path + ".tmp"); d.close(); os.replace(path + ".tmp", path)
    patch(path, b"/QQ 1>>", b"/QQ 1 (junk) 7>>")
    return path
@variant
def broken_objstm_member():
    pdf = plain(); x = pdf.get_new_xref(); pdf.update_object(x, "<< /Junk 1 >>")
    path = save(pdf, "broken_objstm_member", use_objstms=1, compression_effort=0)
    return path  # compressed, can't raw patch easily; baseline for objstm
@variant
def objstm_xrefstm(): return save(plain(3), "objstm_xrefstm", use_objstms=1, garbage=3, deflate=True)
@variant
def incremental_update():
    path = save(plain(), "incremental_update")
    d = fitz.open(path); d[0].insert_text((72, 400), "added later", fontsize=12); d.saveIncr(); d.close(); return path
@variant
def broken_xref():
    path = save(plain(), "broken_xref")
    data = open(path, "rb").read()
    data = re.sub(rb"(\d{10}) 00000 n", lambda m: b"%010d 00000 n" % (int(m.group(1)) + 7), data)
    open(path, "wb").write(data); return path
@variant
def leading_junk():
    path = save(plain(), "leading_junk"); data = open(path, "rb").read()
    open(path, "wb").write(b"JUNKJUNK\r\n" * 30 + data + b"\ntrailing junk"); return path
@variant
def aes_user_password():
    return save(plain(), "aes_user_password", encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="pw", owner_pw="owner",
                permissions=fitz.PDF_PERM_ACCESSIBILITY | fitz.PDF_PERM_PRINT | fitz.PDF_PERM_ANNOTATE | fitz.PDF_PERM_COPY)
@variant
def rc4_copy_forbidden():
    return save(plain(), "rc4_copy_forbidden", encryption=fitz.PDF_ENCRYPT_RC4_128, user_pw="", owner_pw="owner",
                permissions=fitz.PDF_PERM_PRINT | fitz.PDF_PERM_ANNOTATE)
@variant
def annotate_forbidden():
    return save(plain(), "annotate_forbidden", encryption=fitz.PDF_ENCRYPT_AES_128, user_pw="", owner_pw="owner",
                permissions=fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY)
@variant
def existing_links():
    pdf = plain()
    for i in range(3):
        pdf[0].insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(72, 300+i*30, 300, 320+i*30), "uri": f"https://example.com/{i}"})
    pdf[0].insert_link({"kind": fitz.LINK_GOTO, "from": fitz.Rect(72, 120, 300, 145), "page": 1})
    return save(pdf, "existing_links")
@variant
def annots_indirect_array():
    pdf = plain(); a = pdf[0].add_text_annot((300, 300), "old"); a.update()
    path = save(pdf, "annots_indirect_array")
    d = fitz.open(path); px = d[0].xref; arr = d.xref_get_key(px, "Annots")[1]
    ax = d.get_new_xref(); d.update_object(ax, arr); d.xref_set_key(px, "Annots", f"{ax} 0 R")
    d.save(path + ".t"); d.close(); os.replace(path + ".t", path); return path
@variant
def annots_with_junk_entries():
    pdf = plain(); a = pdf[0].add_text_annot((300, 300), "old"); a.update()
    path = save(pdf, "annots_with_junk_entries")
    d = fitz.open(path); px = d[0].xref; arr = d.xref_get_key(px, "Annots")[1]
    junk = d.get_new_xref(); d.update_object(junk, "(i am a string)")
    missing = d.xref_length() + 50
    d.xref_set_key(px, "Annots", arr[:-1] + f" null 42 {junk} 0 R {missing} 0 R]".replace(" 42 ", " 42 "))
    d.save(path + ".t"); d.close(); os.replace(path + ".t", path); return path
@variant
def weird_existing_annots():
    pdf = plain(); p = pdf[0]
    specs = [
        "<< /Type /Annot /Subtype /Text /Rect [300 300 320 320] /Contents (no NM here) /C [0.1 0.2 0.3 0.4] >>",
        "<< /Type /Annot /Subtype /Text /Rect [320 300 340 320] /NM (dup) /Contents (one) /C [0.5] /T (M\\374ller \\(paren\\) back\\\\slash \\\\u00e9) >>",
        "<< /Type /Annot /Subtype /Text /Rect [340 300 360 320] /NM (dup) /Contents <FEFFD55CAE00> /C [] >>",
        "<< /Type /Annot /Subtype /Highlight /Rect [72 120 300 145] /QuadPoints [72 145 300 145 72 120] /NM (oddquads) /Contents (odd quads) >>",
        "<< /Type /Annot /Subtype /Text /Rect [360 300 380 320] /NM (irt-missing) /IRT 9999 0 R /Contents (irt to nowhere) >>",
        "<< /Type /Annot /Subtype /Text /Rect [380 320 360 300] /NM (inverted) /Contents (inverted rect) /CreationDate (garbage date) /M 42 /F (bad) >>",
        "<< /Type /Annot /Subtype /Text /NM (norect) /Contents (no rect at all) >>",
        "<< /Type /Annot /Subtype /Square /Rect [100 500 200 600] /NM (square) /Contents (square) /IC [1 0 0] >>",
        "<< /Type /Annot /Subtype /FreeText /Rect [100 650 300 700] /NM (ft) /Contents (free) /DA (/Helv 12 Tf 0 g) >>",
        "<< /Type /Annot /Subtype /Ink /Rect [100 700 200 760] /NM (ink) /InkList [[100 700 150 750 200 710]] >>",
    ]
    xs = []
    for s in specs:
        x = pdf.get_new_xref(); pdf.update_object(x, s); xs.append(x)
    # IRT cycle
    c1, c2 = pdf.get_new_xref(), pdf.get_new_xref()
    pdf.update_object(c1, f"<< /Type /Annot /Subtype /Text /Rect [400 300 420 320] /NM (cyc1) /IRT {c2} 0 R /Contents (c1) >>")
    pdf.update_object(c2, f"<< /Type /Annot /Subtype /Text /Rect [420 300 440 320] /NM (cyc2) /IRT {c1} 0 R /Contents (c2) >>")
    xs += [c1, c2]
    for x in xs: pdf.xref_set_key(x, "P", f"{p.xref} 0 R")
    pdf.xref_set_key(p.xref, "Annots", "[" + " ".join(f"{x} 0 R" for x in xs) + "]")
    return save(pdf, "weird_existing_annots")
@variant
def shared_annot_two_pages():
    pdf = plain(); a = pdf[0].add_text_annot((300, 300), "shared"); a.update(); ax = a.xref
    pdf.xref_set_key(pdf[1].xref, "Annots", f"[{ax} 0 R]")
    return save(pdf, "shared_annot_two_pages")
@variant
def inherited_rotation():
    pdf = plain(3); path = save(pdf, "inherited_rotation")
    d = fitz.open(path); pages_root = d.pdf_catalog()
    kids = int(d.xref_get_key(pages_root, "Pages")[1].split()[0])
    d.xref_set_key(kids, "Rotate", "90")
    for i in range(len(d)): d.xref_set_key(d[i].xref, "Rotate", "null")
    d.save(path + ".t"); d.close(); os.replace(path + ".t", path); return path
@variant
def form_widgets():
    pdf = plain(); p = pdf[0]
    w = fitz.Widget(); w.field_type = fitz.PDF_WIDGET_TYPE_TEXT; w.field_name = "name"; w.rect = fitz.Rect(72, 400, 300, 430); w.field_value = "홍길동"
    p.add_widget(w); return save(pdf, "form_widgets")
@variant
def broken_content_stream():
    pdf = plain(); p = pdf[0]
    x = p.get_contents()[0]; pdf.update_stream(x, pdf.xref_stream(x) + b"\n BI /W 1 /H 1 3 ID \x00 EI (unterminated")
    return save(pdf, "broken_content_stream")
@variant
def tagged_structtree():
    pdf = plain(); cat = pdf.pdf_catalog()
    st = pdf.get_new_xref(); pdf.update_object(st, "<< /Type /StructTreeRoot /ParentTree << /Nums [] >> /ParentTreeNextKey 0 >>")
    pdf.xref_set_key(cat, "StructTreeRoot", f"{st} 0 R"); pdf.xref_set_key(cat, "MarkInfo", "<< /Marked true >>")
    return save(pdf, "tagged_structtree")
@variant
def many_pages():
    pdf = fitz.open()
    for i in range(300):
        p = pdf.new_page(width=595, height=842); page_text(p, ko=(i % 10 == 0))
    return save(pdf, "many_pages", garbage=3, deflate=True)
@variant
def weird_info_and_metadata():
    pdf = plain(); pdf.set_metadata({"title": "제목 (괄호) \\ 백슬래시", "author": "윤"})
    path = save(pdf, "weird_info_and_metadata")
    return path
@variant
def no_tounicode_type3():
    pdf = fitz.open(); p = pdf.new_page()
    # Type3 font text via a minimal hand-written content
    font = pdf.get_new_xref()
    proc = pdf.get_new_xref(); pdf.update_object(proc, "<< /Length 0 >>"); pdf.update_stream(proc, b"500 0 0 0 500 500 d1 0 0 500 500 re f")
    pdf.update_object(font, f"<< /Type /Font /Subtype /Type3 /FontBBox [0 0 500 500] /FontMatrix [0.001 0 0 0.001 0 0] /CharProcs << /a {proc} 0 R >> /Encoding << /Type /Encoding /Differences [97 /a] >> /FirstChar 97 /LastChar 97 /Widths [500] >>")
    pdf.xref_set_key(p.xref, "Resources", f"<< /Font << /T3 {font} 0 R >> >>")
    c = pdf.get_new_xref(); pdf.update_object(c, "<< >>"); pdf.update_stream(c, b"BT /T3 24 Tf 72 700 Td (aaaa aaa) Tj ET")
    pdf.xref_set_key(p.xref, "Contents", f"{c} 0 R")
    return save(pdf, "no_tounicode_type3")
@variant
def pdf13_plain():
    path = save(plain(), "pdf13_plain"); patch(path, b"%PDF-1.7", b"%PDF-1.3"); return path
@variant
def annot_p_other_page():
    pdf = plain(); a = pdf[0].add_text_annot((300, 300), "p points elsewhere"); a.update()
    pdf.xref_set_key(a.xref, "P", f"{pdf[1].xref} 0 R"); return save(pdf, "annot_p_other_page")
@variant
def popup_broken():
    pdf = plain(); a = pdf[0].add_text_annot((300, 300), "has popup"); a.update()
    pdf.xref_set_key(a.xref, "Popup", "9999 0 R"); return save(pdf, "popup_broken")
@variant
def huge_page():
    pdf = fitz.open(); p = pdf.new_page(width=14000, height=14000); p.insert_text((72, 140), "Alpha big page", fontsize=40)
    return save(pdf, "huge_page")
@variant
def tiny_page():
    pdf = fitz.open(); p = pdf.new_page(width=40, height=30); p.insert_text((2, 20), "Hi", fontsize=10)
    return save(pdf, "tiny_page")

PASSWORDS = {"aes_user_password": "pw"}

def check(name, path):
    problems = []
    d = Document()
    r = d.open(path, PASSWORDS.get(name, ""))
    if r.get("passwordRequired"): return ["password required"]
    info = d.info()
    count = info["count"]
    def step(label, fn):
        try: return fn()
        except Exception as e:
            problems.append(f"{label}: {type(e).__name__}: {e}")
    pages = [0, 1, count - 1] if count > 2 else list(range(count))
    for pg in dict.fromkeys(pages):
        lay = step(f"text_layout p{pg}", lambda: d.text_layout(pg))
        step(f"annotations_page p{pg}", lambda: d.annotations_page(pg))
    if not info["annotatable"]:
        # must refuse politely
        try: d.add_comment(0, [100, 100], "x")
        except Exception as e:
            if "권한" not in str(e): problems.append(f"refusal message: {e}")
        d.close(); return problems or ["(refused as expected)"]
    for pg in dict.fromkeys(pages):
        before = len(d.annotations_page(pg)["items"]) if not problems else None
        r = step(f"add_comment p{pg}", lambda: d.add_comment(pg, [50, 60], "안녕 (괄호) \\ 백슬래시\n둘째 줄", author="사용자"))
        lay = step(f"layout after p{pg}", lambda: d.text_layout(pg))
        if lay and lay["chars"]:
            end = min(len(lay["chars"]), 10)
            for kind in ("highlight", "underline", "strikeout", "squiggly"):
                step(f"add_markup {kind} p{pg}", lambda: d.add_markup(pg, kind, 0, end, author="사용자", content="메모", color="#8ed7ad"))
        items = step(f"annotations_page after p{pg}", lambda: d.annotations_page(pg)["items"]) or []
        mine = [x for x in items if x["name"].startswith("bichaek-")]
        if len(mine) < 1: problems.append(f"p{pg}: comment missing ({len(items)} items)")
        for it in mine[:2]:
            step(f"update p{pg}", lambda: d.update_annotation(pg, it["id"], "수정됨", "검토자", "#7dbbe6", revision=d.revision))
            it2 = next((x for x in d.annotations_page(pg)["items"] if x["name"] == it["name"]), None)
            if not it2 or it2["content"] != "수정됨" or it2["author"] != "검토자": problems.append(f"p{pg}: update not visible {it2 and (it2['content'], it2['author'])}")
            step(f"reply p{pg}", lambda: d.reply_annotation(pg, it2["id"], "답글이에요", "답글러", revision=d.revision))
        texts = [x for x in d.annotations_page(pg)["items"] if x["type"] == "Text" and x["name"].startswith("bichaek-") and not x["reply"]]
        if texts:
            step(f"move p{pg}", lambda: d.move_annotation(pg, texts[0]["id"], [120, 130], d.session, d.revision))
    # edit existing foreign annotations when editable
    for it in d.annotations_page(0)["items"]:
        if it["editable"] and not it["name"].startswith("bichaek-"):
            step(f"edit foreign {it['name'] or it['id']}", lambda: d.update_annotation(0, it["id"], it["content"] + " +", it["author"] or "x", None, revision=d.revision))
    # delete one
    mine = [x for x in d.annotations_page(0)["items"] if x["name"].startswith("bichaek-") and not x["reply"]]
    if mine: step("delete", lambda: d.delete_annotation(0, mine[-1]["id"], revision=d.revision))
    step("undo", d.undo); step("redo", d.redo)
    out = f"{OUT}/{name}-saved.pdf"
    step("save", lambda: d.save(out))
    n_after = len(d.annotations_page(0)["items"])
    d.close()
    # reopen and verify persisted
    try:
        v = fitz.open(out)
        if v.needs_pass: v.authenticate(PASSWORDS.get(name, "owner"))
        names = [a.info.get("id", "") for a in v[0].annots()]
        if not any(n.startswith("bichaek-") for n in names): problems.append("saved file lost comments")
        if v[0].first_annot is None: problems.append("no annots after save")
        # every annotation must still be readable independently
        for a in v[0].annots(): a.info
        v.close()
    except Exception as e:
        problems.append(f"verify saved: {type(e).__name__}: {e}")
    return problems


def handmade(name, objects, root=1, trailer_extra=b""):
    """objects: {num: bytes body}. Writes a classic xref PDF."""
    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"); offs = {}
    for num in sorted(objects):
        offs[num] = len(out); out += b"%d 0 obj\n" % num + objects[num] + b"\nendobj\n"
    n = max(objects) + 1; xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % n
    for i in range(1, n):
        out += (b"%010d 00000 n \n" % offs[i]) if i in offs else b"0000000000 65535 f \n"
    out += b"trailer\n<< /Size %d /Root %d 0 R %s>>\nstartxref\n%d\n%%%%EOF\n" % (n, root, trailer_extra, xref)
    path = f"{OUT}/{name}.pdf"; open(path, "wb").write(bytes(out)); return path

CONTENT = b"BT /F1 24 Tf 72 700 Td (Alpha beta gamma delta) Tj ET"
def base_objects(extra_page=b"", annots=None):
    o = {1: b"<< /Type /Catalog /Pages 2 0 R >>",
         2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
         3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R " + extra_page + b">>",
         4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
         5: b"<< /Length %d >>\nstream\n" % len(CONTENT) + CONTENT + b"\nendstream"}
    return o


@variant
def hand_broken_unused():
    o = base_objects(); o[6] = b"<< /Type /StructElem /S /P /Alt (x) 3 >>"; return handmade("hand_broken_unused", o)
@variant
def hand_broken_info():
    o = base_objects(); o[6] = b"<< /Title (x) /Producer 12 (Hancom) >>"; return handmade("hand_broken_info", o, trailer_extra=b"/Info 6 0 R ")
@variant
def hand_annots_to_broken():
    o = base_objects(b"/Annots [6 0 R 7 0 R] ")
    o[6] = b"<< /Type /Annot /Subtype /Text /Rect [100 100 120 120] /Contents (ok) /NM (ok) >>"
    o[7] = b"<< /Type /Annot /Subtype /Text /Rect [200 100 220 120] 5 /Contents (bad) >>"
    return handmade("hand_annots_to_broken", o)
@variant
def hand_stream_missing_length():
    o = base_objects(); o[5] = b"<< /Length 99 0 R >>\nstream\n" + CONTENT + b"\nendstream"; return handmade("hand_stream_missing_length", o)
@variant
def hand_stream_short_length():
    o = base_objects(); o[5] = b"<< /Length 5 >>\nstream\n" + CONTENT + b"\nendstream"; return handmade("hand_stream_short_length", o)
@variant
def hand_bad_flate_image():
    o = base_objects(); o[3] = o[3].replace(b"/Font << /F1 4 0 R >>", b"/Font << /F1 4 0 R >> /XObject << /Im1 6 0 R >>")
    data = b"\x78\x9cgarbage-not-zlib" * 4
    o[6] = b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length %d >>\nstream\n" % len(data) + data + b"\nendstream"
    c = CONTENT + b" q 100 0 0 100 300 300 cm /Im1 Do Q"
    o[5] = b"<< /Length %d >>\nstream\n" % len(c) + c + b"\nendstream"
    return handmade("hand_bad_flate_image", o)
@variant
def hand_objstm_with_broken_member():
    o = base_objects()
    members = [(6, b"<< /Good 1 >>"), (7, b"<< /Bad 1 (x) 2 >>"), (8, b"[1 2 3]")]
    body = b""; header = b""
    for num, obj in members:
        header += b"%d %d " % (num, len(body)); body += obj + b" "
    data = header + body
    o[9] = b"<< /Type /ObjStm /N 3 /First %d /Length %d >>\nstream\n" % (len(header), len(data)) + data + b"\nendstream"
    # need an xref stream for compressed objects: write classic part then append xref stream manually
    path = handmade("hand_objstm_with_broken_member", o)
    raw = open(path, "rb").read()
    offs = {}
    for m in re.finditer(rb"(\d+) 0 obj", raw): offs[int(m.group(1))] = m.start()
    start = len(raw) - 0
    n = 11
    rows = b""
    import struct
    def row(t, a, b): return struct.pack(">BIH", t, a, b)
    for i in range(n):
        if i == 0: rows += row(0, 0, 65535)
        elif i in (6, 7, 8): rows += row(2, 9, [6, 7, 8].index(i))
        elif i == 10: rows += row(1, start, 0)
        elif i in offs: rows += row(1, offs[i], 0)
        else: rows += row(0, 0, 0)
    xs = b"10 0 obj\n<< /Type /XRef /Size %d /W [1 4 2] /Root 1 0 R /Length %d >>\nstream\n" % (n, len(rows)) + rows + b"\nendstream\nendobj\nstartxref\n%d\n%%%%EOF\n" % start
    raw = raw + xs; open(path, "wb").write(raw); return path
@variant
def hand_gen_numbers():
    o = base_objects()
    path = handmade("hand_gen_numbers", o); raw = open(path, "rb").read()
    raw = raw.replace(b"4 0 obj", b"4 3 obj").replace(b"/F1 4 0 R", b"/F1 4 3 R")
    open(path, "wb").write(raw); return path  # xref now inconsistent -> repair on open




def render_hash(path, pw=""):
    """Page pixels without comment appearances."""
    d = fitz.open(path)
    if d.needs_pass: d.authenticate(pw)
    d.xref_set_key(d[0].xref, "Annots", "null")
    h = hashlib.md5(d[0].get_pixmap(dpi=40, annots=False).samples).hexdigest()
    d.close(); return h


def main():
    shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
    bad = 0
    for name, fn in V.items():
        try: path = fn()
        except Exception as e:
            print(f"!! build {name}: {e}"); traceback.print_exc(); bad += 1; continue
        hand = name.startswith("hand_")
        before = render_hash(path) if hand else None
        try: problems = check(name, path)
        except Exception as e:
            problems = [f"crash: {type(e).__name__}: {e}"]; traceback.print_exc()
        if hand and os.path.exists(f"{OUT}/{name}-saved.pdf") and render_hash(f"{OUT}/{name}-saved.pdf") != before:
            problems.append("page look changed after save")
        ok = not problems or problems == ["(refused as expected)"]
        bad += not ok
        print(("OK  " if ok else "FAIL"), name, "" if ok else "\n      " + "\n      ".join(problems[:12]), flush=True)
    assert not bad, f"{bad} PDF shapes failed"
    print(f"PASS: comments on {len(V)} PDF shapes, saved and reopened", flush=True)


if __name__ == "__main__":
    main()
