"""PDF operations. Only the dedicated engine process may use this module.

SPDX-License-Identifier: AGPL-3.0-or-later
"""
from __future__ import annotations
from contextlib import contextmanager
from collections import OrderedDict
from pathlib import Path
import html
import os
import tempfile
import time
import uuid
import fitz
from .annotations import AnnotationOperations
from .image_objects import ImageObjectOperations
from .fonts import installed_fonts, original_font


class DocumentError(Exception):
    pass


class Document(AnnotationOperations, ImageObjectOperations):
    HISTORY_BUDGET = 384 * 1024 * 1024

    def __init__(self):
        self.pdf = None
        self._display_lists = OrderedDict()
        self._display_stamp = None
        self.path = ""
        self.password = ""
        self.owner_authenticated = False
        self.revision = 0
        self.state_id = 0
        self.saved_id = 0
        self.sequence = 0
        self.session = uuid.uuid4().hex
        self.undo_stack = []
        self.redo_stack = []
        self.pinned = set()
        self.page_tokens = []
        self._pending_tokens = None
        self._editor_font_cache = {}
        self._size_cache = {}
        self.temp = tempfile.TemporaryDirectory(prefix="bichaek-")

    def close(self):
        self._display_lists.clear()
        if self.pdf:
            self.pdf.close()
        self.pdf = None
        self.temp.cleanup()

    def open(self, path, password=""):
        candidate = fitz.open(path)
        if not candidate.is_pdf:
            candidate.close()
            raise DocumentError("PDF 파일만 열 수 있어요.")
        authenticated = 0
        if candidate.needs_pass:
            authenticated = candidate.authenticate(password)
            if not authenticated:
                candidate.close()
                return {"passwordRequired": True}
        if candidate.page_count == 0:
            candidate.close()
            raise DocumentError("페이지가 없는 PDF예요.")
        if self.pdf:
            self.pdf.close()
        self.pdf = candidate
        self.path, self.password = str(Path(path).resolve()), password
        self.owner_authenticated = bool(authenticated & 4)
        for entry in self.undo_stack + self.redo_stack:
            Path(entry[0]).unlink(missing_ok=True)
        self.undo_stack, self.redo_stack = [], []
        self.pinned.clear()
        self._purge_snapshots()
        self.session = uuid.uuid4().hex
        self.page_tokens = [self._token() for _ in range(len(self.pdf))]
        self._editor_font_cache = {}
        self.revision += 1
        self.sequence = self.state_id = self.saved_id = 0
        return self.info()

    def require(self):
        if self.pdf is None:
            raise DocumentError("먼저 PDF를 열어 주세요.")

    def editable(self):
        return bool(self.pdf and (self.owner_authenticated or self.pdf.permissions & fitz.PDF_PERM_MODIFY))

    def info(self):
        self.require()
        return {"name": Path(self.path).name, "path": self.path,
                "count": len(self.pdf), "revision": self.revision,
                "session": self.session, "dirty": self.state_id != self.saved_id,
                "canUndo": bool(self.undo_stack), "canRedo": bool(self.redo_stack),
                "editable": self.editable(), "annotatable": self.annotatable(),
                "printable": bool(self.owner_authenticated or self.pdf.permissions & fitz.PDF_PERM_PRINT),
                "printHighQuality": bool(self.owner_authenticated or self.pdf.permissions & fitz.PDF_PERM_PRINT_HQ),
                "size": list(self.pdf[0].rect)[2:], "pageTokens": list(self.page_tokens),
                "pageSizes": self._page_sizes()}

    def _page_sizes(self):
        """Displayed size of every page, so the reader lays out mixed-size
        documents correctly before each page has been drawn. Cached per page
        content token; only new or changed pages are measured."""
        sizes = []
        for index, token in enumerate(self.page_tokens):
            size = self._size_cache.get(token)
            if size is None:
                rect = self.pdf[index].rect
                size = self._size_cache[token] = [rect.width, rect.height]
            sizes.append(size)
        return sizes

    @staticmethod
    def _token():
        return uuid.uuid4().hex[:12]

    def _snapshot(self):
        name = str(Path(self.temp.name) / (uuid.uuid4().hex + ".pdf"))
        self.pdf.save(name, garbage=0, encryption=fitz.PDF_ENCRYPT_KEEP)
        # Page tokens travel with history so undo/redo can reuse rendered pages.
        return name, self.state_id, list(self.page_tokens)

    def _restore(self, snapshot):
        new = fitz.open(snapshot[0])
        if new.needs_pass and not new.authenticate(self.password):
            new.close()
            raise DocumentError("실행 취소용 문서를 열지 못했어요.")
        self.pdf.close()
        self.pdf = new
        self.state_id = snapshot[1]
        tokens = snapshot[2] if len(snapshot) > 2 else None
        self.page_tokens = list(tokens) if tokens and len(tokens) == len(new) else [self._token() for _ in range(len(new))]

    def _trim_history(self):
        while len(self.undo_stack) > 1 and (
            len(self.undo_stack) > 20 or
            sum(Path(x[0]).stat().st_size for x in self.undo_stack) > self.HISTORY_BUDGET
        ):
            Path(self.undo_stack.pop(0)[0]).unlink(missing_ok=True)

    def _purge_snapshots(self):
        keep = {x[0] for x in self.undo_stack + self.redo_stack} | self.pinned
        if self.pdf and self.pdf.name:
            keep.add(str(Path(self.pdf.name).resolve()))
        for path in Path(self.temp.name).glob("*.pdf"):
            if str(path.resolve()) not in keep:
                try:
                    path.unlink()
                except PermissionError:
                    pass

    @contextmanager
    def transaction(self, annotation=False, pages=None):
        """pages: indices whose appearance changes. Operations that reorder,
        insert or delete pages set self._pending_tokens instead. Without
        either, every page is treated as changed."""
        self.require()
        if not (self.annotatable() if annotation else self.editable()):
            raise DocumentError("이 PDF는 편집 권한이 제한되어 있어요.")
        before = self._snapshot()
        self._pending_tokens = None
        try:
            yield
        except Exception:
            self._restore(before)
            self._purge_snapshots()
            # Windows may hold the restored snapshot open; retain until cleanup.
            raise
        else:
            pending, self._pending_tokens = self._pending_tokens, None
            if pending is not None and len(pending) == len(self.pdf):
                self.page_tokens = pending
            elif pages is not None and len(self.page_tokens) == len(self.pdf):
                for index in set(pages):
                    if 0 <= index < len(self.page_tokens): self.page_tokens[index] = self._token()
            else:
                self.page_tokens = [self._token() for _ in range(len(self.pdf))]
            self.undo_stack.append(before)
            for entry in self.redo_stack:
                try:
                    Path(entry[0]).unlink(missing_ok=True)
                except PermissionError:
                    pass
            self.redo_stack.clear()
            self.sequence += 1
            self.state_id = self.sequence
            self.revision += 1
            self._trim_history()
            self._purge_snapshots()

    def undo(self):
        if not self.undo_stack:
            return self.info()
        self.redo_stack.append(self._snapshot())
        self._restore(self.undo_stack.pop())
        self.revision += 1
        self._purge_snapshots()
        return self.info()

    def redo(self):
        if not self.redo_stack:
            return self.info()
        self.undo_stack.append(self._snapshot())
        self._restore(self.redo_stack.pop())
        self.revision += 1
        self._purge_snapshots()
        return self.info()

    def _pixmap(self, page, width):
        self.require()
        stamp = (self.session,self.revision)
        if self._display_stamp != stamp:
            self._display_lists.clear();self._display_stamp=stamp
        p = self.pdf[page]
        display = self._display_lists.get(page)
        if display is None:
            display = p.get_displaylist(annots=True)
            self._display_lists[page] = display
            if len(self._display_lists)>8:self._display_lists.popitem(last=False)
        self._display_lists.move_to_end(page)
        width = min(3600,max(80,int(width)))
        scale = min(width/p.rect.width,(16_000_000/(p.rect.width*p.rect.height))**.5)
        pix = display.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False,colorspace=fitz.csRGB)
        metadata = {"width":pix.width,"height":pix.height,"stride":pix.stride,
                    "pageWidth":p.rect.width,"pageHeight":p.rect.height,
                    "revision":self.revision,"session":self.session,"page":page,
                    "token":self.page_tokens[page] if page < len(self.page_tokens) else ""}
        return pix,metadata

    def render(self, page, width=1100):
        pix,result = self._pixmap(page,width)
        result["png"] = pix.tobytes("png")
        return result

    def render_frame(self, page, width, shared_name=""):
        pix,result = self._pixmap(page,width)
        if shared_name:
            from multiprocessing.shared_memory import SharedMemory
            frame = SharedMemory(name=shared_name)
            try:
                samples = pix.samples_mv
                if len(samples)>frame.size: raise DocumentError("페이지 이미지가 공유 버퍼보다 큽니다.")
                frame.buf[:len(samples)] = samples
                del samples
                result["shared"] = True
            finally: frame.close()
        else:
            result["png"] = pix.tobytes("png")
        return result

    def inspect_merge(self,path,password=""):
        from .merging import inspect_source
        return inspect_source(path,password)

    def objects(self, page):
        p = self.pdf[page]
        result = []
        traces = p.get_texttrace()
        invisible = [fitz.Rect(t["bbox"]) for t in traces if t["type"] == 3]
        visible = [fitz.Rect(t["bbox"]) for t in traces if t["type"] != 3]
        # Text-only extraction avoids decoding all embedded images into Python.
        data = p.get_text("rawdict", flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)
        for block in data["blocks"]:
            if block["type"] != 0:
                continue
            lines = block.get("lines", [])
            for line in lines:
                for span in line['spans']:
                    span['text']=''.join(c['c'] for c in span['chars'])
            text = "\n".join("".join(s["text"] for s in ln["spans"]) for ln in lines)
            if not text.strip():
                continue
            spans = [s for ln in lines for s in ln["spans"]]
            rect = fitz.Rect(block["bbox"])
            display = rect * p.rotation_matrix
            hidden = any(rect.intersects(r) for r in invisible) and not any(rect.intersects(r) for r in visible)
            runs=[];text_lines=[]
            for index,line in enumerate(lines):
                if index:runs.append({"text":"\n","font":line['spans'][0]['font'],"size":line['spans'][0]['size'],"color":line['spans'][0]['color'],"flags":line['spans'][0]['flags']})
                line_runs=[]
                for span in line['spans']:
                    run={k:span[k] for k in ('text','font','size','color','flags')}
                    run['chars']=[{'c':c['c'],'origin':list(c['origin']),'bbox':list(c['bbox'])} for c in span['chars']]
                    runs.append(run);line_runs.append(run)
                text_lines.append({'runs':line_runs,'origin':list(line['spans'][0]['origin']),'rect':list(line['bbox'])})
            result.append({"runs":runs,"textLines":text_lines,"origin":list(spans[0]['origin']),"id": len(result), "text": text, "rect": list(rect), "hidden": hidden,
                           "displayRect": list(display), "size": spans[0]["size"],
                           "font": spans[0]["font"], "color": spans[0]["color"],
                           "mixedFonts": len({span["font"] for span in spans}) > 1, "page":page, "rotation":p.rotation,
                           "horizontal": all(abs(ln["dir"][0]-1) < .001 and abs(ln["dir"][1]) < .001 for ln in lines)})
        return {"blocks": result, "revision": self.revision, "session": self.session, "page": page}

    @staticmethod
    def native_rect(page, display_rect):
        rect = fitz.Rect(display_rect) * page.derotation_matrix
        unrotated_bounds = page.rect * page.derotation_matrix
        rect = rect & unrotated_bounds
        if rect.is_empty or rect.width < 2 or rect.height < 2:
            raise DocumentError("편집 영역을 조금 더 크게 지정해 주세요.")
        return rect

    @staticmethod
    def _insert_text(page, rect, text, size, color, font_path="", align="left", rotation=0, font_data=None):
        if not text.strip():
            return
        if not (4 <= size <= 200):
            raise DocumentError("글자 크기는 4~200pt로 지정해 주세요.")
        if align not in ("left", "center", "right"):
            raise DocumentError("정렬 값이 올바르지 않아요.")
        css = f"* {{ font-family: sans-serif; font-size: {size}pt; color: #{color:06x}; }} body {{margin:0;padding:0;}} p {{margin:0;line-height:1.12;text-align:{align};}}"
        archive = None
        if font_path:
            from .fonts import font_bytes
            try: font_data = font_bytes(font_path)
            except Exception as exc: raise DocumentError("선택한 글꼴을 읽을 수 없어요: " + str(exc)) from exc
        if font_data:
            try:
                chosen = fitz.Font(fontbuffer=font_data)
                missing = ''.join(sorted({c for c in text if not c.isspace() and not chosen.has_glyph(ord(c))}))
                if missing:
                    raise DocumentError("선택한 글꼴에 다음 글자가 없어요: " + missing[:30] + " · 다른 글꼴을 선택해 주세요.")
                archive = fitz.Archive((font_data, "selected-font"))
                css += "@font-face {font-family:chosen;src:url('selected-font');} * {font-family:chosen;}"
            except DocumentError: raise
            except Exception as exc: raise DocumentError("선택한 글꼴을 읽을 수 없어요: " + str(exc)) from exc
        content = "<p>" + html.escape(text).replace("\n", "<br>") + "</p>"
        spare, scale = page.insert_htmlbox(rect, content, css=css, archive=archive, scale_low=1, rotate=rotation)
        if spare < 0:
            raise DocumentError("텍스트가 영역 안에 들어가지 않아요. 글자 크기를 줄이거나 영역 높이를 늘려 주세요. 변경은 적용하지 않았어요.")

    def editor_fonts(self, page, requests, source='original', path='', block_id=-1):
        """Prepare display fonts for the inline editor.

        Starting the isolated font process costs seconds on Windows, and the
        editor asks again whenever typing adds a character. Reuse a prepared
        program while it still covers the text, and remember characters a
        request already proved unavailable, so only genuinely new work spawns
        a job."""
        from .font_jobs import run_job, snapshot_fonts
        token=self.page_tokens[page] if 0<=page<len(self.page_tokens) else ''
        cache=self._editor_font_cache
        if cache.get('stamp')!=(self.session,token):
            cache.clear();cache['stamp']=(self.session,token)
        result=[];misses={}
        for name,text in requests.items():
            key=(name,source,path)
            entry=cache.get(key)
            needed={ord(c) for c in text if not c.isspace()}
            extra=needed-entry['covers'] if entry else None
            # Reuse while the program covers the text, or while the only
            # uncovered characters are ones an earlier job already found
            # nowhere; typing does not start a new font process each time.
            if entry and extra<=entry['lacking']:
                result.append({'name':name,'data':entry['data'],'family':entry['family'],'error':'','partial':bool(extra),'label':entry.get('label','')})
            else:misses[name]=text
        if misses:
            prepared=run_job({'operation':'prepare','snapshot':snapshot_fonts(self.pdf,page) if source=='original' else {},
                              'requests':misses,'source':source,'path':path})['fonts']
            for item in prepared:
                key=(item['name'],source,path)
                if not item['error']:
                    try:covers=set(fitz.Font(fontbuffer=item['data']).valid_codepoints())
                    except Exception:covers=set()
                    needed={ord(c) for c in misses.get(item['name'],'') if not c.isspace()}
                    old=cache.get(key)
                    lacking=(old['lacking'] if old else set())|(needed-covers if item.get('partial') else set())
                    cache[key]={'data':item['data'],'family':item['family'],'covers':covers,'lacking':lacking,'label':item.get('label','')}
                result.append(item)
        background=b''
        if block_id>=0:
            block=self.objects(page)['blocks'][block_id];rect=fitz.Rect(block['rect'])
            with fitz.open() as temp:
                temp.insert_pdf(self.pdf,from_page=page,to_page=page)
                target=temp[0];target.set_rotation(0);target.add_redact_annot(rect,fill=False,cross_out=False)
                target.apply_redactions(images=0,graphics=0,text=0)
                clip=rect*target.rotation_matrix
                background=target.get_pixmap(matrix=fitz.Matrix(2,2),clip=clip,alpha=False).tobytes('png')
        return {'fonts':result,'background':background}

    def replace_pdf_text(self,page,block_id,fragment,rect,session,revision):
        if session!=self.session or revision!=self.revision:raise DocumentError('문서가 변경되었어요. 본문을 다시 선택해 주세요.')
        blocks=self.objects(page)['blocks']
        if not 0<=block_id<len(blocks):raise DocumentError('수정할 본문을 찾을 수 없어요.')
        block=blocks[block_id];p=self.pdf[page]
        if block['hidden'] or not block['horizontal']:raise DocumentError('이 본문은 직접 수정할 수 없어요.')
        if any(a.type[0]==fitz.PDF_ANNOT_REDACT for a in p.annots() or []):raise DocumentError('적용 전 가림 표시를 먼저 정리해 주세요.')
        target=fitz.Rect(rect);bounds=p.rect*p.derotation_matrix
        if target.is_empty or not (bounds+(-.1,-.1,.1,.1)).contains(target):raise DocumentError('글이 페이지 밖으로 나가요. 편집 영역의 폭이나 글자 크기를 조정해 주세요.')
        with self.transaction(pages=[page]):
            p=self.pdf[page];p.add_redact_annot(fitz.Rect(block['rect']),fill=False,cross_out=False)
            p.apply_redactions(images=0,graphics=0,text=0)
            if fragment:
                with fitz.open(stream=fragment,filetype='pdf') as text_pdf:
                    if len(text_pdf)!=1:raise DocumentError('편집 결과를 배치하지 못했어요.')
                    p.show_pdf_page(target,text_pdf,0,keep_proportion=False,overlay=True,
                        clip=fitz.Rect(0,0,target.width,target.height))
        return self.info()

    def replace_text_runs(self,page,block_id,runs,fonts,rect,session,revision):
        """Replace a paragraph with positioned characters written as PDF text.

        runs: [{font, size, color, chars: [[x, y, char], ...]}] with baseline
        positions in points relative to rect's top-left; fonts: {font: bytes}."""
        if session!=self.session or revision!=self.revision:raise DocumentError('문서가 변경되었어요. 본문을 다시 선택해 주세요.')
        blocks=self.objects(page)['blocks']
        if not 0<=block_id<len(blocks):raise DocumentError('수정할 본문을 찾을 수 없어요.')
        block=blocks[block_id];p=self.pdf[page]
        if block['hidden'] or not block['horizontal']:raise DocumentError('이 본문은 직접 수정할 수 없어요.')
        if p.rotation:raise DocumentError('회전된 페이지는 이 방식으로 적용할 수 없어요.')
        if any(a.type[0]==fitz.PDF_ANNOT_REDACT for a in p.annots() or []):raise DocumentError('적용 전 가림 표시를 먼저 정리해 주세요.')
        target=fitz.Rect(rect)
        if target.is_empty or not (p.rect+(-.1,-.1,.1,.1)).contains(target):raise DocumentError('글이 페이지 밖으로 나가요. 편집 영역의 폭이나 글자 크기를 조정해 주세요.')
        from .fonts import pdf_font
        loaded={key:fitz.Font(fontbuffer=pdf_font(data)) for key,data in fonts.items()}
        with self.transaction(pages=[page]):
            p=self.pdf[page];p.add_redact_annot(fitz.Rect(block['rect']),fill=False,cross_out=False)
            p.apply_redactions(images=0,graphics=0,text=0)
            placed=[(run,x,y,char) for run in runs for x,y,char in run['chars']]
            writers={}
            for run,x,y,char in placed:
                font=loaded[run['font']];size=float(run['size'])
                if not font.has_glyph(ord(char)):continue   # never stamp a .notdef box
                colour=tuple(float(c) for c in run['color'])
                writer=writers.get(colour)
                if writer is None:writer=writers[colour]=fitz.TextWriter(p.rect)
                writer.append(fitz.Point(target.x0+x,target.y0+y),char,font=font,fontsize=size)
            for colour,writer in writers.items():writer.write_text(p,color=colour)
        return self.info()

    def font_preview(self, page, name, text, source, path):
        if source=='original':
            return {'font':original_font(self.pdf,page,name,text)}
        if path:
            from .fonts import font_bytes, qt_font
            return {'font':qt_font(font_bytes(path))[0]}
        return {'font':b''}

    def available_fonts(self):
        from .font_jobs import font_catalog
        return font_catalog()

    def replace_text(self, page, block_id, text, size, color=0x202124, font_path="", height=None, revision=None, font_source="default"):
        if revision is not None and revision != self.revision:
            raise DocumentError("문서가 변경되었어요. 텍스트를 다시 선택해 주세요.")
        blocks = self.objects(page)["blocks"]
        if not 0 <= block_id < len(blocks):
            raise DocumentError("선택한 텍스트를 찾지 못했어요.")
        block = blocks[block_id]
        if block.get("hidden"):
            raise DocumentError("OCR의 보이지 않는 문자층이에요. 원본 스캔 이미지의 글자는 이 편집 기능으로 바꿀 수 없어요.")
        if not block["horizontal"]:
            raise DocumentError("기울어진 텍스트는 첫 버전에서 직접 교체할 수 없어요.")
        p = self.pdf[page]
        if any(a.type[0] == fitz.PDF_ANNOT_REDACT for a in p.annots() or []):
            raise DocumentError("적용 전인 가림 처리 표시가 있는 페이지예요. 원본에서 해당 표시를 정리한 뒤 편집해 주세요.")
        font_data = None
        if font_source == "original" and not font_path and text.strip():
            if block.get("mixedFonts"):
                raise DocumentError("이 블록에는 여러 글꼴이 있어요. 적용할 글꼴을 직접 선택해 주세요.")
            try: font_data = original_font(self.pdf, page, block["font"], text)
            except ValueError as exc: raise DocumentError(str(exc)) from exc
        original = fitz.Rect(block["rect"])
        target = fitz.Rect(original)
        target.y1 = min((p.rect * p.derotation_matrix).y1,
                        target.y0 + max(original.height + 4, float(height or original.height + 6)))
        with self.transaction(pages=[page]):
            p = self.pdf[page]
            # Physically remove text, preserving artwork and vector backgrounds.
            p.add_redact_annot(original, fill=False, cross_out=False)
            p.apply_redactions(images=0, graphics=0, text=0)
            self._insert_text(p, target, text, float(size), int(color), font_path, font_data=font_data)
        return self.info()

    def add_text(self, page, rect, text, size=14, color=0x202124, font_path=""):
        with self.transaction(pages=[page]):
            p = self.pdf[page]
            self._insert_text(p, self.native_rect(p, rect), text, float(size), int(color), font_path, rotation=p.rotation)
        return self.info()

    def move_page(self, source, target):
        self.require()
        if not (0 <= source < len(self.pdf) and 0 <= target < len(self.pdf)):
            raise DocumentError("페이지 위치가 올바르지 않아요.")
        if source != target:
            with self.transaction():
                # move_page's destination means insert-before in pre-move indices.
                self.pdf.move_page(source, target if source > target else target + 1 if target < len(self.pdf)-1 else -1)
                tokens = list(self.page_tokens); tokens.insert(target, tokens.pop(source))
                self._pending_tokens = tokens
        return self.info()

    def move_pages(self, pages, target, revision=None):
        self.require()
        if revision is not None and revision != self.revision: raise DocumentError("페이지 구성이 바뀌었어요. 다시 선택해 주세요.")
        selected=sorted(set(map(int,pages))); count=len(self.pdf)
        if not selected or selected[0]<0 or selected[-1]>=count or not 0<=target<=count:
            raise DocumentError("이동할 페이지와 위치를 확인해 주세요.")
        remaining=[i for i in range(count) if i not in set(selected)]
        start=target-sum(i<target for i in selected)
        order=remaining[:start]+selected+remaining[start:]
        if order != list(range(count)):
            with self.transaction():
                current=list(range(count))
                for dest, value in enumerate(order):
                    source=current.index(value)
                    if source != dest:
                        self.pdf.move_page(source,dest)
                        current.insert(dest,current.pop(source))
                self._pending_tokens=[self.page_tokens[i] for i in order]
        result=self.info();result['movedSelection']=list(range(start,start+len(selected)))
        return result

    def delete_pages(self, pages):
        pages = sorted(set(map(int, pages)))
        if not pages or pages[0] < 0 or pages[-1] >= len(self.pdf):
            raise DocumentError("삭제할 페이지를 선택해 주세요.")
        if len(pages) >= len(self.pdf):
            raise DocumentError("문서에 한 페이지 이상 남아 있어야 해요.")
        with self.transaction():
            self.pdf.delete_pages(pages)
            self._pending_tokens = [t for i, t in enumerate(self.page_tokens) if i not in set(pages)]
        return self.info()

    def rotate(self, pages, angle=90):
        with self.transaction(pages=[int(x) for x in pages]):
            for index in sorted(set(map(int, pages))):
                p = self.pdf[index]
                p.set_rotation((p.rotation + int(angle)) % 360)
        return self.info()

    def insert_pdf(self, path, at):
        other = fitz.open(path)
        try:
            if other.needs_pass:
                raise DocumentError("삽입할 PDF는 암호를 먼저 해제해 주세요.")
            if not other.is_pdf or not len(other):
                raise DocumentError("삽입할 PDF를 확인해 주세요.")
            with self.transaction():
                before = len(self.pdf)
                self.pdf.insert_pdf(other, start_at=int(at))
                where = int(at) if 0 <= int(at) <= before else before
                self._pending_tokens = (self.page_tokens[:where] + [self._token() for _ in range(len(self.pdf)-before)]
                                        + self.page_tokens[where:])
        finally:
            other.close()
        return self.info()

    def add_image(self, page, rect, path):
        with self.transaction(pages=[page]):
            p = self.pdf[page]
            p.insert_image(self.native_rect(p, rect), filename=path, keep_proportion=True, rotate=p.rotation)
            name, form = self._image_form(p, p.get_contents()[-1])
        result=self.info(); result["imageFocus"]={"page":page,"id":str(form)}
        return result

    def highlight(self, page, rect):
        p = self.pdf[page]
        area = self.native_rect(p, rect)
        words = [fitz.Rect(w[:4]) for w in p.get_text("words") if fitz.Rect(w[:4]).intersects(area)]
        if not words:
            raise DocumentError("영역 안에 선택 가능한 글자가 없어요. 스캔 문서는 OCR을 먼저 실행해 주세요.")
        with self.transaction(annotation=True, pages=[page]):
            a = p.add_highlight_annot(words)
            self._new_annotation_info(a, "사용자", "", "#ffd54f", "형광펜")
        return self.info()

    def note(self, page, rect, text):
        return self.add_comment(page, list(rect[:2]), text)

    def search_page(self, page, query):
        p = self.pdf[page]
        rects = [list(r * p.rotation_matrix) for r in p.search_for(query)]
        return {"page": page, "rects": rects, "revision": self.revision, "session": self.session}

    def selected_text(self, page, rect):
        p = self.pdf[page]
        if not self.owner_authenticated and not self.pdf.permissions & fitz.PDF_PERM_COPY:
            raise DocumentError("이 PDF는 텍스트 복사가 제한되어 있어요.")
        return {"text": p.get_textbox(self.native_rect(p, rect))}

    def page_links(self, page):
        p = self.pdf[page]
        links = []
        for link in p.get_links():
            # MuPDF already returns annotation and destination coordinates in
            # displayed (rotated) space. Applying rotation again would be wrong.
            item = {"rect": list(link["from"])}
            if link["kind"] == fitz.LINK_URI:
                item.update(kind="uri", uri=link.get("uri", ""))
            elif link["kind"] == fitz.LINK_GOTO and link.get("page", -1) >= 0:
                point = link.get("to", fitz.Point(0, 0))
                item.update(kind="page", page=link["page"], point=list(point))
            elif link["kind"] == fitz.LINK_NAMED:
                name = link.get("nameddest", link.get("name", ""))
                destination = {"NextPage": page+1, "PrevPage": page-1,
                               "FirstPage": 0, "LastPage": len(self.pdf)-1}.get(name)
                if destination is None:
                    try:
                        destination, x, y = self.pdf.resolve_link("#" + name)
                    except Exception:
                        destination = -1
                item.update(kind="page", page=destination, point=[0, 0])
            else:
                item.update(kind="unsupported")
            links.append(item)
        return links

    def outline(self):
        """Bookmarks for the reader sidebar. Page is 0-based, -1 if unresolved."""
        self.require()
        items = []
        for entry in self.pdf.get_toc(simple=False):
            level, title, page = entry[0], entry[1], entry[2] - 1
            y = 0.0
            dest = entry[3] if len(entry) > 3 and isinstance(entry[3], dict) else {}
            point = dest.get("to")
            if 0 <= page < len(self.pdf) and point is not None:
                # MuPDF reports the target in unrotated page space (top-left
                # origin). The reader scrolls in displayed space. Clamp so a
                # malformed destination cannot scroll past the page.
                p = self.pdf[page]
                shown = fitz.Point(point) * p.rotation_matrix
                y = min(max(0.0, float(shown.y)), float(p.rect.height))
            items.append({"level": max(1, int(level)), "title": " ".join(str(title).split()) or "(제목 없음)",
                          "page": page if 0 <= page < len(self.pdf) else -1, "y": y})
        return {"items": items, "revision": self.revision, "session": self.session}

    def render_print(self, page, dpi=300):
        self.require()
        if not self.owner_authenticated and not self.pdf.permissions & fitz.PDF_PERM_PRINT:
            raise DocumentError("이 PDF는 인쇄 권한이 제한되어 있어요.")
        if not self.owner_authenticated and not self.pdf.permissions & fitz.PDF_PERM_PRINT_HQ:
            dpi = min(dpi, 150)
        return self.render(page, round(self.pdf[page].rect.width * min(300, dpi) / 72))

    def image_metadata(self, page):
        p = self.pdf[page]
        images = []
        for info in p.get_image_info():
            rect = (fitz.Rect(info["bbox"]) * p.rotation_matrix) & p.rect
            if rect.is_empty or rect.is_infinite: continue
            images.append({"number": info["number"], "page": page, "rect": list(rect),
                "width": info["width"], "height": info["height"],
                "session": self.session, "revision": self.revision, "pageId": p.xref})
        return images

    def extract_embedded_image(self, page, number, revision, session, page_id):
        self.require()
        if session != self.session or revision != self.revision or self.pdf[page].xref != page_id:
            raise DocumentError("문서가 변경되었어요. 이미지를 다시 선택해 주세요.")
        if not (self.owner_authenticated or self.pdf.permissions & fitz.PDF_PERM_COPY):
            raise DocumentError("이 문서는 이미지 복사와 저장을 허용하지 않아요.")
        p = self.pdf[page]
        info = next((i for i in p.get_image_info(xrefs=True) if i["number"] == number), None)
        if not info: raise DocumentError("선택한 이미지를 찾을 수 없어요.")
        if info["width"] * info["height"] > 100_000_000:
            raise DocumentError("이미지가 너무 커요. 1억 화소 이하의 이미지만 복사할 수 있어요.")
        xref = info.get("xref", 0)
        if xref:
            data = self.pdf.extract_image(xref)
            pix = fitz.Pixmap(data["image"])
            mask = data.get("smask", 0)
            if mask:
                if pix.alpha: pix = fitz.Pixmap(pix, 0)
                pix = fitz.Pixmap(pix, fitz.Pixmap(self.pdf, mask))
        else:
            # Inline PDF images have no xref. Decode only for explicit copy/save.
            block = next((b for b in p.get_text("dict", flags=fitz.TEXT_PRESERVE_IMAGES)["blocks"]
                          if b.get("type") == 1 and b.get("number") == number), None)
            if not block: raise DocumentError("이 이미지 형식은 추출할 수 없어요.")
            pix = fitz.Pixmap(block["image"])
            if block.get("mask"):
                if pix.alpha: pix = fitz.Pixmap(pix, 0)
                pix = fitz.Pixmap(pix, fitz.Pixmap(block["mask"]))
        if pix.colorspace is None: raise DocumentError("단독 이미지가 아닌 마스크예요.")
        if pix.colorspace.n != 3: pix = fitz.Pixmap(fitz.csRGB, pix)
        return {"png": pix.tobytes("png"), "width": pix.width, "height": pix.height}

    def text_layout(self, page):
        """Character boxes in displayed coordinates; no OCR or image decoding."""
        self.require()
        p = self.pdf[page]
        allowed = bool(self.owner_authenticated or self.pdf.permissions & fitz.PDF_PERM_COPY)
        result = {"page": page, "pageId": p.xref, "session": self.session,
                  "revision": self.revision, "copyable": allowed, "chars": [], "lines": [],
                  "links": self.page_links(page), "annotations": self.annotations_page(page)["items"], "images": [],
                  "movableImages": self.movable_images(page) if self.editable() else []}
        if not allowed:
            return result
        result["images"] = self.image_metadata(page)
        data = p.get_text("rawdict", flags=fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES,
                          sort=True)
        matrix = p.rotation_matrix
        for block in data["blocks"]:
            for line in block.get("lines", []):
                start = len(result["chars"])
                line_id = len(result["lines"])
                for span in line["spans"]:
                    for char in span["chars"]:
                        rect = fitz.Rect(char["bbox"]) * matrix
                        result["chars"].append([char["c"], *list(rect), line_id])
                if len(result["chars"]) > start:
                    dx, dy = line.get("dir", (1, 0))
                    result["lines"].append({"start": start, "end": len(result["chars"]),
                        "rect": list(fitz.Rect(line["bbox"]) * matrix),
                        "dx": dx * matrix.a + dy * matrix.c,
                        "dy": dx * matrix.b + dy * matrix.d})
        result["hasText"] = any(c[0].strip() for c in result["chars"])
        return result

    def save(self, path):
        self.require()
        target = Path(path).resolve()
        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")
        fd, tmp = tempfile.mkstemp(prefix=".bichaek-save-", suffix=".pdf", dir=target.parent)
        os.close(fd)
        os.unlink(tmp)
        same_path = target == Path(self.path)
        try:
            # Full rewrite removes orphaned old text streams; never rasterize pages.
            self.pdf.save(tmp, garbage=3, deflate=True, encryption=fitz.PDF_ENCRYPT_KEEP)
            check = fitz.open(tmp)
            if check.needs_pass:
                check.authenticate(self.password)
            if len(check) != len(self.pdf):
                check.close()
                raise DocumentError("저장한 PDF 검증에 실패했어요.")
            check.close()
            # Close the source handle before replacing on Windows. Keep a recovery
            # snapshot so a failed replace cannot lose the in-memory document.
            recovery = self._snapshot()
            self.pdf.close()
            try:
                os.replace(tmp, target)
            except Exception:
                self.pdf = fitz.open(recovery[0])
                if self.pdf.needs_pass:
                    self.pdf.authenticate(self.password)
                raise
            self.pdf = fitz.open(target)
            if self.pdf.needs_pass:
                self.pdf.authenticate(self.password)
            self.path = str(target)
            self.saved_id = self.state_id
            # Full-save compaction may renumber annotation xrefs. Invalidate
            # all handles, selection targets and cached document geometry.
            self.revision += 1
            self._purge_snapshots()
        finally:
            Path(tmp).unlink(missing_ok=True)
        return self.info()

    def ocr_snapshot(self):
        self.require()
        path = self._snapshot()[0]
        self.pinned.add(path)
        return {"path": path, "password": self.password,
                "session": self.session, "revision": self.revision}

    def release_snapshot(self, path):
        self.pinned.discard(path)
        self._purge_snapshots()
        return {}

    def merge_ocr(self, results, revision, session):
        if revision != self.revision or session != self.session:
            raise DocumentError("OCR 중 문서가 바뀌어서 인식 결과를 적용하지 않았어요. 현재 문서에서 다시 실행해 주세요.")
        if not results:
            return self.info()
        with self.transaction(pages=[item["page"] for item in results]):
            for item in results:
                p = self.pdf[item["page"]]
                layer = fitz.open(item["path"])
                rotation = p.rotation
                p.set_rotation(0)
                p.show_pdf_page(p.rect, layer, 0)
                p.set_rotation(rotation)
                layer.close()
        return self.info()
