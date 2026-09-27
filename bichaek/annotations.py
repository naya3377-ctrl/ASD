"""PDF-native comments. No private sidecar or flattened page drawings.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from collections import Counter
from datetime import datetime, timezone
import math
import re
import uuid
import fitz


LABELS = {"Text": "메모", "Highlight": "형광펜", "Underline": "밑줄",
          "StrikeOut": "취소선", "Squiggly": "물결 밑줄", "FreeText": "텍스트 상자",
          "Ink": "펜", "Square": "사각형", "Circle": "타원", "Line": "선",
          "Stamp": "스탬프", "Caret": "삽입 표시", "FileAttachment": "첨부 파일",
          "Redact": "가림 표시"}
EDITABLE = {"Text", "Highlight", "Underline", "StrikeOut", "Squiggly"}
MARKUP = {"highlight": "add_highlight_annot", "underline": "add_underline_annot",
          "strikeout": "add_strikeout_annot", "squiggly": "add_squiggly_annot"}
LOCKS = fitz.PDF_ANNOT_IS_READ_ONLY | fitz.PDF_ANNOT_IS_LOCKED | fitz.PDF_ANNOT_IS_LOCKED_CONTENTS
mupdf = fitz.mupdf


# Keys are written straight into the annotation dictionary. PyMuPDF's
# xref_set_key prints the whole dictionary, edits the text and parses it back,
# which a foreign annotation with unusual content does not always survive.
def _obj(a): return mupdf.pdf_annot_obj(a.this)
def put_text(a, key, text): mupdf.pdf_dict_puts(_obj(a), key, mupdf.pdf_new_text_string(text))
def put_name(a, key, name): mupdf.pdf_dict_puts(_obj(a), key, mupdf.pdf_new_name(name))
def drop_key(a, key): mupdf.pdf_dict_dels(_obj(a), key)
def raw_rect(a):
    r = mupdf.pdf_dict_get_rect(_obj(a), mupdf.pdf_new_name("Rect"))
    return fitz.Rect(r.x0, r.y0, r.x1, r.y1)
def put_rect(a, rect):
    mupdf.pdf_dict_put_rect(_obj(a), mupdf.pdf_new_name("Rect"), mupdf.FzRect(*map(float, rect)))


def pdf_date():
    return datetime.now(timezone.utc).strftime("D:%Y%m%d%H%M%S+00'00'")


def color_rgb(value):
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(value)):
        raise ValueError("주석 색상을 확인해 주세요.")
    return tuple(int(value[i:i+2], 16)/255 for i in (1, 3, 5))


def color_hex(value):
    if len(value) == 1: value = value * 3
    elif len(value) == 4:
        c, m, y, k = value
        value = [1-min(1, c+k), 1-min(1, m+k), 1-min(1, y+k)]
    if len(value) != 3: return "#ffd54f"
    return "#" + "".join(f"{round(max(0, min(1, v))*255):02x}" for v in value)


class AnnotationOperations:
    def annotatable(self):
        return bool(self.pdf and (self.owner_authenticated or self.pdf.permissions & fitz.PDF_PERM_ANNOTATE))

    def _annotation(self, page, identifier):
        p = self.pdf[page]
        matches = []
        for a in p.annots() or []:
            key = "nm:" + a.info["id"] if a.info.get("id") else "xref:" + str(a.xref)
            if key == identifier or identifier == "xref:" + str(a.xref): matches.append(a)
        if len(matches) != 1: raise ValueError("주석이 바뀌었어요. 목록에서 다시 선택해 주세요.")
        # Retain the page object as long as the annotation is being used.
        return p, matches[0]

    def _annotation_editable(self, a):
        return (self.annotatable() and a.type[1] in EDITABLE and not a.flags & LOCKS and
                self.pdf.xref_get_key(a.xref, "StateModel")[0] == "null" and
                self.pdf.xref_get_key(a.xref, "RT")[1] != "/Group")

    def annotations_page(self, page):
        self.require()
        p = self.pdf[page]
        annots = list(p.annots() or [])
        names = Counter(a.info.get("id", "") for a in annots)
        identifiers = {a.xref: ("nm:"+a.info["id"] if a.info.get("id") and names[a.info["id"]] == 1
                               else "xref:"+str(a.xref)) for a in annots}
        result = []
        context = {"textpage": None}
        for a in annots:
            try:
                if a.type[1] in ("Popup", "Link", "Widget"): continue
                result.append(self._describe_annotation(p, page, a, identifiers, context))
            except Exception:
                # One damaged foreign comment must not hide the others or the
                # page's text layer: list it read-only with what can be read.
                from .diagnostics import failure
                failure("annotation %s on page %d" % (a.xref, page + 1))
                result.append(self._damaged_annotation(p, page, a, identifiers))
        # A grouped primary is also read-only: editing it independently would
        # incorrectly change shared group attributes.
        group_parents = {x["parentId"] for x in result if x["grouped"]}
        for item in result:
            if item["id"] in group_parents: item["editable"] = False
        return {"page": page, "items": result, "session": self.session, "revision": self.revision}

    def _describe_annotation(self, p, page, a, identifiers, context):
        info = a.info
        subtype = a.type[1]
        rect = a.rect * p.rotation_matrix
        regions, quote = [], []
        if subtype in ("Highlight", "Underline", "StrikeOut", "Squiggly"):
            vertices = a.vertices or []
            for pos in range(0, len(vertices)-3, 4):
                quad = fitz.Quad(vertices[pos:pos+4])
                regions.append(list((quad * p.rotation_matrix).rect))
                if self.owner_authenticated or self.pdf.permissions & fitz.PDF_PERM_COPY:
                    if context["textpage"] is None: context["textpage"] = p.get_textpage()
                    quote.append(p.get_textbox(quad.rect, textpage=context["textpage"]).strip())
        rt = self.pdf.xref_get_key(a.xref, "RT")[1]
        state = self.pdf.xref_get_key(a.xref, "State")[1]
        state_model = self.pdf.xref_get_key(a.xref, "StateModel")[1]
        parent = identifiers.get(a.irt_xref, "")
        grouped = rt == "/Group"
        return {"id": identifiers[a.xref], "name": info.get("id", ""), "page": page,
            "type": subtype, "label": LABELS.get(subtype, subtype), "rect": list(rect),
            "regions": regions or [list(rect)], "content": info.get("content", ""),
            "author": info.get("title", ""), "subject": info.get("subject", ""),
            "created": info.get("creationDate", ""), "modified": info.get("modDate", ""),
            "color": color_hex(a.colors.get("stroke") or []), "opacity": a.opacity if a.opacity >= 0 else 1,
            "parentId": parent, "reply": bool(parent and not grouped), "grouped": grouped,
            "state": state if state_model != "null" else "", "editable": self._annotation_editable(a),
            "quote": "\n".join(quote)[:500], "flags": a.flags,
            "session": self.session, "revision": self.revision}

    def _damaged_annotation(self, p, page, a, identifiers):
        def read(fn, default):
            try: return fn()
            except Exception: return default
        rect = read(lambda: list(a.rect * p.rotation_matrix), [0, 0, 0, 0])
        info = read(lambda: a.info, {})
        subtype = read(lambda: a.type[1], "Annot")
        return {"id": identifiers.get(a.xref, "xref:"+str(a.xref)), "name": info.get("id", ""), "page": page,
            "type": subtype, "label": LABELS.get(subtype, subtype), "rect": rect, "regions": [rect],
            "content": info.get("content", ""), "author": info.get("title", ""), "subject": info.get("subject", ""),
            "created": info.get("creationDate", ""), "modified": info.get("modDate", ""),
            "color": "#ffd54f", "opacity": 1, "parentId": "", "reply": False, "grouped": False,
            "state": "", "editable": False, "quote": "", "flags": read(lambda: a.flags, 0),
            "session": self.session, "revision": self.revision}

    def _new_annotation_info(self, a, author, content, color, subject):
        now = pdf_date()
        a.set_info(title=author.strip() or "사용자", content=content, subject=subject,
                   creationDate=now, modDate=now)
        put_text(a, "NM", "bichaek-"+uuid.uuid4().hex)
        a.set_colors(stroke=color_rgb(color))
        a.set_flags(a.flags | fitz.PDF_ANNOT_IS_PRINT)
        a.update()

    def _annotation_result(self, page, a):
        state = self.info()
        state["annotationFocus"] = {"page": page, "id": "nm:"+a.info["id"]}
        return state

    def add_markup(self, page, kind, start, end, author="사용자", content="", color="#ffd54f"):
        if kind not in MARKUP: raise ValueError("지원하지 않는 텍스트 주석이에요.")
        # Marking text needs its position, not its characters: a PDF that
        # allows comments but not copying can still be highlighted.
        if not self.annotatable(): raise ValueError("이 PDF는 주석 권한이 제한되어 있어요.")
        color_rgb(color)
        p = self.pdf[page]
        data = p.get_text("rawdict", flags=fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES, sort=True)
        quads, count = [], 0
        start, end = sorted((int(start), int(end)))
        for block in data["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    chars = span["chars"]
                    selected = chars[max(0, start-count):max(0, min(len(chars), end-count))]
                    if selected: quads.append(fitz.recover_span_quad(line["dir"], span, chars=selected))
                    count += len(chars)
        if not quads or start < 0 or end > count:
            raise ValueError("먼저 주석을 남길 글자를 드래그해 선택해 주세요.")
        with self.transaction(annotation=True, pages=[page]):
            a = getattr(p, MARKUP[kind])(quads)
            self._new_annotation_info(a, author, content, color, LABELS[a.type[1]])
        return self._annotation_result(page, a)

    def add_comment(self, page, point, content, author="사용자", color="#ffd54f"):
        if not content.strip(): raise ValueError("메모 내용을 입력해 주세요.")
        color_rgb(color)
        if len(point) != 2 or not all(math.isfinite(float(x)) for x in point):
            raise ValueError("메모 위치를 확인해 주세요.")
        p = self.pdf[page]
        point = fitz.Point(point) * p.derotation_matrix
        with self.transaction(annotation=True, pages=[page]):
            a = p.add_text_annot(point, content, icon="Comment")
            self._new_annotation_info(a, author, content, color, "메모")
        return self._annotation_result(page, a)

    def update_annotation(self, page, identifier, content, author, color=None, revision=None):
        if revision != self.revision: raise ValueError("문서가 바뀌었어요. 주석을 다시 선택해 주세요.")
        p, a = self._annotation(page, identifier)
        item = next(x for x in self.annotations_page(page)["items"] if x["id"] == identifier)
        if not item["editable"]: raise ValueError("이 주석은 읽기 전용이거나 지원하지 않는 형식이에요.")
        if color is not None: color_rgb(color)
        with self.transaction(annotation=True, pages=[page]):
            old = a.info
            a.set_info(content=content, title=author, modDate=pdf_date())
            if content != old.get("content", ""):
                # Plain-text edits replace an old rich-text popup body, which
                # Acrobat would otherwise prefer over the updated /Contents.
                drop_key(a, "RC")
            if not old.get("id"):
                put_text(a, "NM", "bichaek-"+uuid.uuid4().hex)
            if color is not None and color.lower() != item["color"].lower():
                a.set_colors(stroke=color_rgb(color))
                a.update()
            # Preserve existing /AP, popup, review and vendor-specific fields
            # when only comment text or author changed.
        return self._annotation_result(page, a)

    def reply_annotation(self, page, identifier, content, author="사용자", revision=None):
        if revision != self.revision: raise ValueError("문서가 바뀌었어요. 주석을 다시 선택해 주세요.")
        if not content.strip(): raise ValueError("답글 내용을 입력해 주세요.")
        p, parent = self._annotation(page, identifier)
        item = next(x for x in self.annotations_page(page)["items"] if x["id"] == identifier)
        if not item["editable"]: raise ValueError("이 주석에는 답글을 추가할 수 없어요.")
        with self.transaction(annotation=True, pages=[page]):
            a = p.add_text_annot(parent.rect.tl, content, icon="Comment")
            self._new_annotation_info(a, author, content, item["color"], "답글")
            a.set_irt_xref(parent.xref)
            put_name(a, "RT", "R")
            # Replies belong in the comment thread, without another page icon.
            a.set_flags(fitz.PDF_ANNOT_IS_NO_VIEW | fitz.PDF_ANNOT_IS_NO_ZOOM | fitz.PDF_ANNOT_IS_NO_ROTATE)
        return self._annotation_result(page, a)

    def move_annotation(self, page, identifier, point, session, revision):
        if session != self.session or revision != self.revision: raise ValueError("문서가 바뀌었어요. 메모를 다시 선택해 주세요.")
        p,a=self._annotation(page,identifier)
        if a.type[1]!='Text' or not self._annotation_editable(a): raise ValueError("이 메모는 이동할 수 없어요.")
        if len(point)!=2 or not all(math.isfinite(float(v)) for v in point): raise ValueError("메모 위치를 확인해 주세요.")
        old=a.rect*p.rotation_matrix
        x=max(0,min(float(point[0]),p.rect.width-old.width))
        y=max(0,min(float(point[1]),p.rect.height-old.height))
        if not __import__('math').isfinite(x+y): raise ValueError("메모 위치를 확인해 주세요.")
        with self.transaction(annotation=True, pages=[page]):
            # Text icons carry NoRotate. set_rect reanchors their fixed-size
            # appearance on rotated pages; translate the stored PDF rect instead.
            matrix = p.derotation_matrix * ~p.transformation_matrix
            delta = fitz.Point(x,y)*matrix - old.tl*matrix
            put_rect(a, raw_rect(a) + fitz.Rect(delta.x,delta.y,delta.x,delta.y))
            a.set_info(modDate=pdf_date())
            a.update()
        return self._annotation_result(page,a)

    def delete_annotation(self, page, identifier, revision=None):
        if revision != self.revision: raise ValueError("문서가 바뀌었어요. 주석을 다시 선택해 주세요.")
        items = self.annotations_page(page)["items"]
        target = next((x for x in items if x["id"] == identifier), None)
        if not target or not target["editable"]: raise ValueError("이 주석은 삭제할 수 없어요.")
        descendants, order = {identifier}, [identifier]
        while True:
            children = [x["id"] for x in items if x["parentId"] in descendants and x["id"] not in descendants]
            if not children: break
            descendants.update(children); order.extend(children)
        if any(not x["editable"] for x in items if x["id"] in descendants):
            raise ValueError("연결된 답글에 잠기거나 지원하지 않는 항목이 있어 삭제하지 않았어요.")
        with self.transaction(annotation=True, pages=[page]):
            for key in reversed(order):
                p, a = self._annotation(page, key)
                p.delete_annot(a)
        return self.info()
