"""One live QTextDocument drives both inline editing and the PDF text fragment.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import base64, hashlib, math, time
from shiboken6 import isValid
from .text_geometry import build_lines,SPACING
from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer, QByteArray, QBuffer, QIODevice, QSizeF, QMarginsF, QRectF
from PySide6.QtGui import (QTextDocument,QTextCursor,QTextCharFormat,QTextFormat,QTextBlockFormat,
    QFont,QFontDatabase,QRawFont,QColor,QImage,QPdfWriter,QPageSize,QPainter)

ORIGIN=int(QTextFormat.UserProperty)+1
SIZE=int(QTextFormat.UserProperty)+2
FLAGS=int(QTextFormat.UserProperty)+3
FALLBACK=int(QTextFormat.UserProperty)+5



# Qt font registrations are shared by every editor and tab and kept until the
# app exits. Removing one while a text layout or glyph cache still refers to
# it can make Qt draw or save the wrong glyphs (seen as NUL characters when
# editors were opened and closed in a row). A byte budget bounds the total.
_FONT_REGISTRY={}
_FONT_BYTES=0
_FONT_BUDGET=192*1024*1024

def register_font(data):
    """Register a font program once per app; returns (family, QRawFont, id)."""
    global _FONT_BYTES
    key=hashlib.sha256(data).hexdigest()
    if key not in _FONT_REGISTRY:
        if _FONT_BYTES+len(data)>_FONT_BUDGET:raise ValueError('열어 둔 글꼴이 많아요. 문서를 저장하고 앱을 다시 열어 주세요.')
        font_id=QFontDatabase.addApplicationFontFromData(QByteArray(data))
        families=QFontDatabase.applicationFontFamilies(font_id)
        if not families:raise ValueError('글꼴을 화면에 표시할 수 없어요. 다른 글꼴을 선택해 주세요.')
        raw=QRawFont();raw.loadFromData(QByteArray(data),20,QFont.PreferNoHinting)
        if not raw.isValid():raise ValueError('글꼴을 읽을 수 없어요. 다른 글꼴을 선택해 주세요.')
        _FONT_REGISTRY[key]=(families[0],raw,font_id);_FONT_BYTES+=len(data)
    return _FONT_REGISTRY[key]

class TextEditor(QObject):
    changed=Signal()
    widthChanged=Signal()
    applyFailed=Signal()
    def __init__(self,bridge):
        super().__init__(bridge);self.bridge=bridge;self.target={};self.doc=None;self.fonts={};self.raw={}
        self.ids={};self.generation=0;self._ready=False;self._status='';self._background=''
        self._width=1.;self._height=1.;self._offset=0.;self._edited=False;self._size=14.;self._loading=False
        self._guard=False;self._font_error=False;self._fallback=False;self._auto_tried='';self._wrappers=[];self.device=QImage(1,1,QImage.Format_ARGB32)
        self.device.setDotsPerMeterX(3780);self.device.setDotsPerMeterY(3780)
        self._missing_stamp=None;self._missing='';self._has_fallback=False;self._support={};self._measuring=False
        self._registered={};self.font_data={};self._composing=False;self._pending_font=None;self._fallback_failed=False
        self.resume=QTimer(self);self.resume.setSingleShot(True);self.resume.timeout.connect(self._resume_fonts)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(160);self.timer.timeout.connect(lambda:self.useFallback(True))
        self.watchdog=QTimer(self);self.watchdog.setSingleShot(True);self.watchdog.setInterval(25000);self.watchdog.timeout.connect(self._timed_out)
    @Property(bool,notify=changed)
    def ready(self):return self._ready
    @Property(str,notify=changed)
    def status(self):return self._status
    @Property(str,notify=changed)
    def background(self):return self._background
    @Property(float,notify=widthChanged)
    def width(self):return self._width
    @Property(float,notify=changed)
    def height(self):return self._height
    @Property(float,notify=changed)
    def offset(self):return self._offset
    @Property(bool,notify=changed)
    def edited(self):return self._edited
    @Property(bool,notify=changed)
    def canApply(self):return self._ready and not self._composing and not self._loading and not self._font_error and not self._invalid() and self._height<=self._max_height()+.01
    @Property(bool,notify=changed)
    def loading(self):return self._loading
    @Property(bool,notify=changed)
    def canUseFallback(self):return self._ready and not self._loading and bool(self._invalid())
    def _fail(self,message):
        self.watchdog.stop();self._loading=False;self._guard=False;self._font_error=True
        self._status=message;self.changed.emit()
    def _timed_out(self):
        if not self._loading:return
        self.generation+=1
        self._fail('글꼴 확인 응답이 지연됐어요. 입력 내용과 원문은 유지돼요. 다시 시도하거나 취소해 주세요.')
    @Slot()
    def retry(self):self.loadFonts()
    @Slot(bool)
    def setComposing(self,value):
        self._composing=value
        if value:self.timer.stop()
        elif self._pending_font:self.resume.start(0)
        elif self._ready and self._invalid():self.timer.start()
        self.changed.emit()
    def _resume_fonts(self):
        if self._composing:return
        pending=self._pending_font;self._pending_font=None
        if pending and not self._composing:pending[0](pending[1])
    def _invalidate_glyphs(self):
        self._missing_stamp=None;self._support.clear()
    def _register(self,data):
        key=hashlib.sha256(data).hexdigest()
        if key not in self._registered:
            family,raw,font_id=register_font(data)
            self.ids[key]=font_id;self._registered[key]=(family,raw)
        return self._registered[key]
    def _max_height(self):
        return self.target.get('pageHeight',20000)-self.target.get('rect',[0,0])[1]
    def start(self,target):
        self._detach()
        self.resume.stop();self._pending_font=None;self._composing=False;self._invalidate_glyphs()
        self.generation+=1;self.timer.stop();self.target=dict(target);self._ready=False;self._loading=False
        self._background='';self._status='원본 글꼴을 확인하는 중…';self._edited=False;self._offset=0;self._font_error=False;self._fallback=False;self._auto_tried='';self._fallback_failed=False
        self._width=max(20,target['rect'][2]-target['rect'][0]+.5);self._height=max(10,target['rect'][3]-target['rect'][1])
        self._size=target.get('size',14);self.fonts={};self._opened=time.monotonic()
        fallback=self.raw.get('__fallback__');self.raw={'__fallback__':fallback} if fallback else {}
        data=getattr(self,'font_data',{}).get('__fallback__');self.font_data={'__fallback__':data} if data else {}
        self.widthChanged.emit()
        old=self.doc;self.doc=None
        if old:old.deleteLater()
        self.changed.emit()
    def stop(self):
        self.resume.stop();self._pending_font=None;self._composing=False;self._invalidate_glyphs()
        self.generation+=1;self.timer.stop();self.watchdog.stop();self.target={};self._ready=False;self._loading=False;self.changed.emit()
        self._detach()
    def _detach(self):
        # QQuickTextEdit does not own an externally supplied QTextDocument.
        # Disconnect every surviving view before the next edit deletes that document.
        self._wrappers=[pair for pair in self._wrappers if isValid(pair[0])]
        for wrapper,blank in self._wrappers:
            if wrapper.textDocument() is self.doc:wrapper.setTextDocument(blank)
    def _fragments(self):
        if not self.doc:return []
        result=[];block=self.doc.begin()
        while block.isValid():
            it=block.begin()
            while not it.atEnd():
                fragment=it.fragment()
                if fragment.isValid():result.append((fragment.position(),fragment.length(),fragment.text(),fragment.charFormat()))
                it+=1
            block=block.next()
        return result
    def _requests(self):
        result={}
        if self.doc:
            for pos,length,text,fmt in self._fragments():
                name=fmt.property(ORIGIN) or self.target.get('font','');result[name]=result.get(name,'')+text
        else:
            for run in self.target.get('runs',[]) or [self.target]:
                name=run.get('font','');result[name]=result.get(name,'')+run.get('text','')
        return result or {self.target.get('font',''):''}
    def loadFonts(self):
        if not self.target:return
        self.generation+=1;token=self.generation;target=dict(self.target);self._loading=True;self._auto_tried=''
        self._status='글꼴을 확인하는 중…';self.watchdog.start();self.changed.emit()
        def got(result):
            if token!=self.generation or self.bridge.closed:return
            if self._composing:self.watchdog.stop();self._pending_font=(got,result);return
            if result.get('stale'):
                self._fail('문서 상태가 바뀌었어요. 취소 후 본문을 다시 선택해 주세요.');return
            had_document=self.doc is not None
            try:
                self.watchdog.stop();self._loading=False;errors=[]
                for entry in result['fonts']:
                    if entry['error']:errors.append(entry['error']);continue
                    family,raw=self._register(entry['data']);self.fonts[entry['name']]=family;self.raw[entry['name']]=raw;self.font_data[entry['name']]=entry['data']
                self._invalidate_glyphs()
                if result.get('background'):self._background='data:image/png;base64,'+base64.b64encode(result['background']).decode('ascii')
                if errors:
                    self._fail(' · '.join(dict.fromkeys(errors)));return
                self._font_error=False
                self._guard=True
                if self.doc is None:self._build()
                else:self._reformat()
                self._guard=False;self._ready=True;self._status='';self._measure();self.changed.emit()
                if not had_document:
                    from .diagnostics import note
                    note('text editor ready in %.2fs (%d characters)',time.monotonic()-getattr(self,'_opened',time.monotonic()),len(self.doc.toPlainText()))
                self.bridge._editor_font_family=next(iter(self.fonts.values()),'');self.bridge.fontsChanged.emit()
                # Characters the chosen/original font lacks are shown in a
                # Korean fallback right away instead of blocking the edit.
                if self._invalid():self.timer.start()
            except Exception:
                from .diagnostics import failure
                failure('Preparing inline text')
                if not had_document and self.doc is not None:
                    self._detach();self.doc.deleteLater();self.doc=None;self._ready=False
                self._fail('본문 편집을 준비하지 못했어요. 원문은 유지돼요. 다른 글꼴을 선택하거나 다시 시도해 주세요.')
            finally:self._guard=False
        def failed(message):
            if token==self.generation:self._fail(message)
        self.bridge.command('editor_fonts',{'page':target['page'],'requests':self._requests(),
            'source':self.bridge._font_choice,'path':self.bridge._font_path,
            'block_id':target.get('id',-1) if not self._background else -1},got,guarded=True,error_callback=failed)
    def _format(self,name,size,color,flags):
        fmt=QTextCharFormat();font=QFont(self.fonts.get(name,''));font.setPointSizeF(size*.75)
        styles=QFontDatabase.styles(font.family())
        if styles:font.setStyleName(styles[0])
        if self.bridge._font_choice=='original':font.setBold(bool(flags&16));font.setItalic(bool(flags&2))
        font.setStyleStrategy(QFont.PreferDefault);font.setHintingPreference(QFont.PreferNoHinting)
        fmt.setFont(font);fmt.setForeground(QColor(color));fmt.setProperty(ORIGIN,name);fmt.setProperty(SIZE,size);fmt.setProperty(FLAGS,flags)
        return fmt
    def _build(self):
        self.doc=QTextDocument(self);self.doc.setDocumentMargin(0);self.doc.documentLayout().setPaintDevice(self.device)
        cursor=QTextCursor(self.doc);cursor.beginEditBlock()
        if self.target.get('textLines') and self.bridge._font_choice=='original':
            build_lines(self,cursor)
        else:
            for run in self.target.get('runs',[]) or [self.target]:
                fmt=self._format(run.get('font',''),run.get('size',self._size),'#%06x'%run.get('color',0x202124),run.get('flags',0))
                cursor.insertText(run.get('text',''),fmt)
        cursor.endEditBlock();first=QTextCursor(self.doc);first.setPosition(0);self.doc.setDefaultFont(first.charFormat().font())
        self.doc.setTextWidth(self._width);self.doc.clearUndoRedoStacks()
        self.doc.contentsChanged.connect(self._contents_changed)
        self.doc.documentLayout().documentSizeChanged.connect(self._measure)
        # Align the first original baseline, retaining the PDF's starting position.
        first=self.doc.begin().layout()
        if first.lineCount() and self.target.get('origin'):
            self._offset=self.target['origin'][1]-self.target['rect'][1]-first.position().y()-first.lineAt(0).y()-first.lineAt(0).ascent()
    def _reformat(self):
        cursor=QTextCursor(self.doc);cursor.beginEditBlock()
        for pos,length,text,old in self._fragments():
            name=old.property(ORIGIN) or self.target.get('font','')
            fmt=self._format(name,float(old.property(SIZE) or self._size),old.foreground().color().name(),int(old.property(FLAGS) or 0))
            if old.hasProperty(SPACING):
                fmt.setProperty(SPACING,old.property(SPACING))
                if self.bridge._font_choice=='original':
                    font=fmt.font();font.setKerning(False);font.setStyleStrategy(QFont.PreferNoShaping);fmt.setFont(font)
                    fmt.setFontLetterSpacingType(QFont.AbsoluteSpacing);fmt.setFontLetterSpacing(float(old.property(SPACING)))
            cursor.setPosition(pos);cursor.setPosition(pos+length,QTextCursor.KeepAnchor);cursor.setCharFormat(fmt)
        cursor.endEditBlock()
    def _invalid(self):
        stamp=(id(self.doc),self.doc.revision() if self.doc else -1)
        if self._missing_stamp==stamp:return self._missing
        missing=set()
        self._has_fallback=False
        for pos,length,text,fmt in self._fragments():
            fallback=bool(fmt.property(FALLBACK));self._has_fallback|=fallback
            name='__fallback__' if fallback else fmt.property(ORIGIN) or self.target.get('font','')
            font=self.raw.get(name)
            for char in set(text):
                if char.isspace():continue
                key=(name,char)
                if key not in self._support:self._support[key]=bool(font and font.supportsCharacter(ord(char)))
                if not self._support[key]:missing.add(char)
        self._missing_stamp=stamp;self._missing=''.join(sorted(missing))
        return self._missing
    @Slot()
    def useFallback(self,automatic=False):
        if self._composing:return
        missing=self._invalid()
        if not self.canUseFallback:return
        if automatic:
            # Never loop on characters no available font can show (emoji etc.).
            if missing==self._auto_tried and self._font_error:return
            self._auto_tried=missing
        self.generation+=1;token=self.generation;self.timer.stop();self._loading=True
        self._status='추가한 글자를 표시할 글꼴을 준비하는 중…';self.watchdog.start();self.changed.emit()
        def got(result):
            if token!=self.generation or self.bridge.closed:return
            if self._composing:self.watchdog.stop();self._pending_font=(got,result);return
            try:
                if result.get('stale'):raise ValueError('문서가 바뀌었어요. 본문을 다시 선택해 주세요.')
                entry=result['fonts'][0]
                if entry['error']:raise ValueError(entry['error'])
                family,raw=self._register(entry['data']);self.raw['__fallback__']=raw;self.font_data['__fallback__']=entry['data']
                self._fallback_entry=entry;self._invalidate_glyphs()
                self._guard=True;cursor=QTextCursor(self.doc);cursor.beginEditBlock()
                try:
                    for pos,length,text,fmt in self._fragments():
                        original=self.raw.get('__fallback__' if fmt.property(FALLBACK) else fmt.property(ORIGIN) or self.target.get('font',''))
                        offset=0
                        for char in text:
                            count=len(char.encode('utf-16-le'))//2
                            if not char.isspace() and (not original or not original.supportsCharacter(ord(char))):
                                replacement=QTextCharFormat(fmt);font=fmt.font();font.setFamilies([family]);font.setStyleName('')
                                font.setBold(bool(int(fmt.property(FLAGS) or 0)&16));font.setItalic(bool(int(fmt.property(FLAGS) or 0)&2))
                                font.setLetterSpacing(QFont.AbsoluteSpacing,0);replacement.setFont(font);replacement.setProperty(FALLBACK,True)
                                cursor.setPosition(pos+offset);cursor.setPosition(pos+offset+count,QTextCursor.KeepAnchor);cursor.setCharFormat(replacement)
                            offset+=count
                finally:cursor.endEditBlock();self._guard=False
                self._loading=False;self._font_error=False;self._edited=self._edited or not automatic;self.watchdog.stop()
                left=self._invalid()
                self._status=('이 글자는 사용할 수 있는 글꼴이 없어요: '+left[:20]) if left else '원본 글꼴에 없는 글자는 '+(entry.get('label') or self._fallback_label())+'(으)로 표시했어요. 위쪽 글꼴 목록에서 바꿀 수 있어요.'
                self._font_error=bool(left);self._fallback_failed=bool(left);self._measure()
                if left and left!=self._auto_tried:self.timer.start()
            except Exception as exc:self._fail(str(exc))
        raw=self.raw.get('__fallback__')
        if raw and all(raw.supportsCharacter(ord(c)) for c in missing):
            got({'fonts':[self._fallback_entry]});return
        self.bridge.command('editor_fonts',{'page':self.target['page'],'requests':{'__fallback__':missing},
            'source':'fallback','path':self._fallback_path(),'block_id':-1},got,guarded=True,error_callback=lambda message:self._fail(message) if token==self.generation else None)
    def _fallback_path(self):
        finder=getattr(self.bridge,'fallback_font_path',None)
        return finder() if finder else ''
    def _fallback_label(self):
        finder=getattr(self.bridge,'fallback_label',None)
        return finder() if finder else '기본 한글 글꼴'
    def _contents_changed(self):
        if self._guard:return
        self._edited=True;missing=self._invalid()
        if missing:
            self._status='새 글자('+missing[:20]+')에 맞는 글꼴을 준비하는 중…'
            if not self._composing and not self._loading:self.timer.start()
        else:
            if self._fallback_failed:self._font_error=False;self._fallback_failed=False
            self._status='일부 추가 글자는 대체 글꼴로 표시하고 있어요.' if self._has_fallback else ''
            self.timer.stop()
        self._measure()
    def _measure(self,*args):
        if self._guard or self._measuring:return
        self._measuring=True
        try:self._measure_now(*args)
        finally:self._measuring=False
    def _measure_now(self,*args):
        if self.doc and self.target:
            size=args[0] if args and isinstance(args[0],QSizeF) else self.doc.size()
            self._height=max(self.target['rect'][3]-self.target['rect'][1],size.height()+max(0,self._offset)+1)
            if self._height>self._max_height():self._status='글이 페이지 밖으로 나가요. 오른쪽 손잡이로 폭을 넓히거나 글자 크기를 줄여 주세요.'
            elif not self._status:
                for rect in self.target.get('neighbors',[]):
                    x,y=self.target['rect'][:2]
                    if rect[1]>=self.target['rect'][3]-.5 and y+self._height>rect[1] and x+self._width>rect[0] and x<rect[2]:
                        self._status='아래 본문과 겹쳐요. 편집 영역의 폭이나 글자 크기를 조정해 주세요.';break
        self.changed.emit()
    @Slot(QObject,int)
    def attach(self,wrapper,page):
        if self.doc is not None and self.target.get('page')==page:
            self._wrappers=[pair for pair in self._wrappers if isValid(pair[0])]
            if not any(w is wrapper for w,blank in self._wrappers):
                self._wrappers.append((wrapper,QTextDocument(wrapper)))
            wrapper.setTextDocument(self.doc)
            # QQuickTextEdit may set its default width; keep base PDF-point coordinates.
            self.doc.documentLayout().setPaintDevice(self.device);self.doc.setTextWidth(self._width)
    @Slot(float)
    def setWidth(self,width):
        if not self.doc:return
        self._width=max(20,min(float(width),self.target.get('pageWidth',20000)-self.target['rect'][0]))
        self.widthChanged.emit()
        self.doc.setTextWidth(self._width);self._edited=True;self._status='';self._measure()
    @Slot(float)
    def setSize(self,size):
        if not self.doc or not 4<=size<=200 or abs(size-self._size)<.001:return
        ratio=size/self._size;self._size=size;self._guard=True;cursor=QTextCursor(self.doc);cursor.beginEditBlock()
        for pos,length,text,fmt in self._fragments():
            value=float(fmt.property(SIZE) or size/ratio)*ratio;fmt.setProperty(SIZE,value);font=fmt.font();font.setPointSizeF(value*.75);fmt.setFont(font)
            if fmt.hasProperty(SPACING):
                spacing=float(fmt.property(SPACING))*ratio;fmt.setProperty(SPACING,spacing)
                if self.bridge._font_choice=='original':fmt.setFontLetterSpacing(spacing)
            cursor.setPosition(pos);cursor.setPosition(pos+length,QTextCursor.KeepAnchor);cursor.setCharFormat(fmt)
        block=self.doc.begin()
        while block.isValid():
            fmt=block.blockFormat()
            if fmt.lineHeight()>0:
                fmt.setLineHeight(fmt.lineHeight()*ratio,fmt.lineHeightType());QTextCursor(block).setBlockFormat(fmt)
            block=block.next()
        cursor.endEditBlock();self._guard=False;self._edited=True;self._offset=0;self._status='';self._measure()
    def text_runs(self):
        """The laid-out text as positioned characters, in PDF points relative to
        the edit box. The PDF engine writes these as real text with the same
        font programs. Qt's own PDF output is not used for this: on Windows it
        can draw converted fonts as outlines, which then cannot be selected,
        searched or edited again."""
        runs=[];current=None
        for pos,length,text,fmt in self._fragments():
            block=self.doc.findBlock(pos);layout=block.layout();base=layout.position()
            key='__fallback__' if fmt.property(FALLBACK) else fmt.property(ORIGIN) or self.target.get('font','')
            size=float(fmt.property(SIZE) or self._size);colour=fmt.foreground().color()
            style=(key,round(size,3),colour.rgb())
            offset=pos-block.position()
            for char in text:
                units=len(char.encode('utf-16-le'))//2
                # Spaces are written too, so copied/searched text keeps its word breaks.
                if char not in '\n\r\t\u2028\u2029\ufffc':
                    line=layout.lineForTextPosition(offset)
                    if line.isValid():
                        x=base.x()+line.cursorToX(offset)[0];y=base.y()+line.y()+line.ascent()+self._offset
                        if current is None or current['style']!=style:
                            current={'style':style,'font':key,'size':size,'color':[colour.redF(),colour.greenF(),colour.blueF()],'chars':[]};runs.append(current)
                        current['chars'].append([x,y,char])
                offset+=units
        for run in runs:del run['style']
        return runs
    def pdf_bytes(self):
        if not self.doc.toPlainText().strip():return b''
        data=QByteArray();buffer=QBuffer(data);buffer.open(QIODevice.WriteOnly)
        # QPdfWriter rounds its MediaBox to integer points. Round outward and
        # crop on insertion, otherwise stretching to the fractional target
        # silently changes character positions after applying the edit.
        writer=QPdfWriter(buffer);writer.setResolution(72);writer.setPageSize(QPageSize(QSizeF(math.ceil(self._width),math.ceil(self._height)),QPageSize.Point));writer.setPageMargins(QMarginsF(0,0,0,0));writer.setCreator('YoonDF 1.0.7')
        painter=QPainter(writer)
        if not painter.isActive():raise ValueError('편집 내용을 PDF로 만들지 못했어요.')
        painter.translate(0,self._offset);self.doc.drawContents(painter,QRectF(0,0,self._width,self._height-self._offset));painter.end();buffer.close()
        return bytes(data)
    def apply(self):
        if not self.canApply:return
        if not self._edited and self.bridge._font_choice=='original':self.bridge.textCommitted.emit();return
        target=self.target;rect=list(target['rect']);rect[2]=rect[0]+self._width;rect[3]=rect[1]+self._height
        direct=not target.get('rotation',0)
        try:
            if direct:
                runs=self.text_runs();used={r['font'] for r in runs}
                missing=[k for k in used if k not in self.font_data]
                if missing:raise ValueError('글꼴 정보를 찾지 못했어요. 다시 시도해 주세요.')
                fonts={k:self.font_data[k] for k in used}
            else:data=self.pdf_bytes()
        except Exception as exc:self._status=str(exc);self.changed.emit();self.applyFailed.emit();return
        self.bridge._busy=True;self.bridge.stateChanged.emit()
        applied=time.monotonic()
        def done(state):
            from .diagnostics import note;note('edit applied in %.2fs',time.monotonic()-applied)
            self.bridge.update_state(state);self.bridge.set_status('화면에서 편집한 내용을 적용했어요. Ctrl+S로 저장하세요.');self.bridge.textCommitted.emit()
        def failed(message):self.bridge._busy=False;self.bridge.stateChanged.emit();self._status=message;self.changed.emit();self.applyFailed.emit()
        if direct:
            self.bridge.command('replace_text_runs',{'page':target['page'],'block_id':target['id'],'runs':runs,'fonts':fonts,'rect':rect,
                'session':target['session'],'revision':target['revision']},done,error_callback=failed)
        else:
            self.bridge.command('replace_pdf_text',{'page':target['page'],'block_id':target['id'],'fragment':data,'rect':rect,
                'session':target['session'],'revision':target['revision']},done,error_callback=failed)
    def dispose(self):
        self.generation+=1;self.timer.stop();self.watchdog.stop();self.resume.stop();self._pending_font=None
        self._detach()
        # Registrations are shared and kept for the app's lifetime (register_font).
