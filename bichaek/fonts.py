"""Resolve complete, collection and PDF-subset font programs without substitution.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from functools import lru_cache
from pathlib import Path
from io import BytesIO
import os, re, unicodedata, hashlib
import fitz
from fontTools.ttLib import TTFont, TTCollection, newTable
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable


def normalized(name):
    name = re.sub(r"^[A-Z]{6}\+", "", name).lstrip("~")
    return "".join(c for c in unicodedata.normalize("NFKC", name).casefold() if c.isalnum())


def font_bytes(key):
    path, sep, index = key.rpartition("#face=")
    if not sep: return Path(key).read_bytes()
    font=TTFont(path,fontNumber=int(index),recalcTimestamp=False);out=BytesIO();font.save(out);font.close();return out.getvalue()


def names_of(font):
    names=font['name'];aliases=set()
    for rec in names.names:
        if rec.nameID in (1,2,4,6,16,17):
            try: aliases.add(rec.toUnicode())
            except Exception: pass
    family=names.getBestFamilyName() or ''
    style=names.getBestSubFamilyName() or 'Regular'
    full=names.getBestFullName() or family
    # Bare family is an exact match only for the regular face.
    exact={n.toUnicode() for n in names.names if n.nameID in (4,6) and n.isUnicode()}
    if style.casefold() in ('regular','normal','book','roman'):
        exact.update(n.toUnicode() for n in names.names if n.nameID in (1,16) and n.isUnicode())
    return family,style,full,sorted(aliases),sorted(exact)


@lru_cache(maxsize=1)
def installed_fonts():
    if os.name=='nt':
        roots=[Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts',Path(os.environ.get('LOCALAPPDATA',''))/'Microsoft/Windows/Fonts']
    else:
        roots=[Path('/usr/share/fonts'),Path('/usr/local/share/fonts'),Path.home()/'.local/share/fonts',Path.home()/'.fonts',Path('/Library/Fonts'),Path('/System/Library/Fonts')]
    paths=set()
    for root in roots:
        if root.is_dir():paths.update(p for p in root.rglob('*') if p.suffix.lower() in ('.ttf','.otf','.ttc','.otc') and p.is_file())
    if os.name=='nt':
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE,winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(hive,r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts') as key:
                    for i in range(winreg.QueryInfoKey(key)[1]):
                        value=winreg.EnumValue(key,i)[1]
                        if isinstance(value,str):
                            path=Path(value)
                            if path.is_absolute() and path.is_file():paths.add(path)
            except OSError:pass
    result=[]
    for path in sorted(paths):
        try:
            if path.suffix.lower() in ('.ttc','.otc'):
                collection=TTCollection(path,lazy=True);faces=collection.fonts
            else:collection=None;faces=[TTFont(path,lazy=True)]
            for index,font in enumerate(faces):
                family,style,label,aliases,exact=names_of(font)
                result.append({'label':label,'name':label,'family':family,'style':style,'aliases':aliases,'exact':exact,
                    'key':str(path)+(f'#face={index}' if collection else '')})
            if collection:collection.close()
            else:faces[0].close()
        except Exception:continue
    return sorted(result,key=lambda r:(r['label'].casefold(),r['key']))


def _unicode_map(stream):
    """The relevant bfchar/bfrange subset of a PDF ToUnicode CMap."""
    result={}
    def put(cid,hextext):
        try:
            text=bytes.fromhex(hextext.decode()).decode('utf-16-be')
            if len(text)==1 and ord(text)!=0xfffd:result[cid]=ord(text)
        except (ValueError,UnicodeError):pass
    for block in re.findall(rb'beginbfchar(.*?)endbfchar',stream,re.S):
        for a,b in re.findall(rb'<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>',block):put(int(a,16),b)
    for block in re.findall(rb'beginbfrange(.*?)endbfrange',stream,re.S):
        for a,b,values in re.findall(rb'<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>\s*(<[^>]+>|\[[^]]*\])',block,re.S):
            lo,hi=int(a,16),int(b,16)
            if hi-lo>65535:continue
            if values.startswith(b'['):
                for cid,value in zip(range(lo,hi+1),re.findall(rb'<([0-9a-fA-F]+)>',values)):put(cid,value)
            else:
                base=values[1:-1]
                for cid in range(lo,hi+1):put(cid,format(int(base,16)+cid-lo,'0'+str(len(base))+'x').encode())
    return result


def _cid_glyphs(doc,xref,font):
    if doc.xref_get_key(xref,'Encoding')[1] not in ('/Identity-H','/Identity-V'):return {}
    uk,uv=doc.xref_get_key(xref,'ToUnicode');dk,dv=doc.xref_get_key(xref,'DescendantFonts')
    if uk!='xref' or dk!='array':return {}
    refs=re.findall(r'(\d+)\s+0\s+R',dv)
    if len(refs)!=1:return {}
    descendant=int(refs[0]);kind,value=doc.xref_get_key(descendant,'CIDToGIDMap')
    mapping=doc.xref_stream(int(value.split()[0])) if kind=='xref' else None
    cmap=_unicode_map(doc.xref_stream(int(uv.split()[0])));glyphs=font.getGlyphOrder();out={}
    for cid,cp in cmap.items():
        if mapping is not None:gid=int.from_bytes(mapping[cid*2:cid*2+2],'big') if cid*2+2<=len(mapping) else 0
        elif 'glyf' in font:gid=cid
        else:
            name='cid'+str(cid).zfill(5);gid=font.getGlyphID(name) if name in glyphs else 0
        if 0<gid<len(glyphs):
            name=glyphs[gid]
            if 'glyf' in font and not chr(cp).isspace() and font['glyf'][name].numberOfContours==0:continue
            out[cp]=name
    return out


def repair_embedded(doc,page,entry,data):
    try:
        font=TTFont(BytesIO(data),recalcTimestamp=False);cmap=(font.getBestCmap() or {}) if 'cmap' in font else {};recovered=_cid_glyphs(doc,entry[0],font)
        if not recovered:
            # Trace IDs are safe only when this page has one program for the name.
            siblings=[f for f in doc[page].get_fonts(full=True) if normalized(f[3])==normalized(entry[3])]
            if len({f[0] for f in siblings})==1:
                order=font.getGlyphOrder()
                for span in doc[page].get_texttrace():
                    if normalized(span['font'])==normalized(entry[3]):
                        for cp,gid,*rest in span['chars']:
                            if cp!=0xfffd and 0<gid<len(order):recovered[cp]=order[gid]
        if recovered:
            # Font outlines are unchanged. Restore Unicode addressing only.
            cmap.update(recovered);table=newTable('cmap');table.tableVersion=0
            sub=CmapSubtable.newSubtable(12);sub.platformID=3;sub.platEncID=10;sub.language=0;sub.cmap=cmap;table.tables=[sub];font['cmap']=table
            out=BytesIO();font.save(out);font.close();return out.getvalue()
        font.close()
    except Exception:pass
    return data


def has_text(data,text):
    try:
        font=fitz.Font(fontbuffer=data)
        return all(c.isspace() or font.has_glyph(ord(c)) for c in text)
    except Exception:return False


def original_font(document,page,name,text):
    key=normalized(name)
    # Embedded program is authoritative; do not pick a different installed version first.
    for entry in document[page].get_fonts(full=True):
        if normalized(entry[3])==key:
            data=document.extract_font(entry[0])[3]
            if data:
                data=repair_embedded(document,page,entry,data)
                if has_text(data,text):return data
    for row in installed_fonts():
        if key in {normalized(n) for n in row.get('exact',[row['name']])}:
            data=font_bytes(row['key'])
            if has_text(data,text):return data
    for builtin in ['helv','hebo','heit','hebi','tiro','tibo','tiit','tibi','cour','cobo','coit','cobi','symb','zadb']:
        font=fitz.Font(builtin)
        if name in fitz.Base14_fontdict and normalized(fitz.Font(name).name)==normalized(font.name) or key==normalized(font.name):
            if has_text(font.buffer,text):return font.buffer
    raise ValueError(f'“{name}”에 필요한 글자가 없거나 원본 글꼴을 읽을 수 없어요. 같은 글꼴을 설치하거나 검색해서 선택해 주세요.')


def qt_font(data):
    """Wrap bare PDF CFF and use a unique family, avoiding Qt family collisions."""
    try:font=TTFont(BytesIO(data),recalcTimestamp=False)
    except Exception:
        from fontTools.cffLib import CFFFontSet
        from fontTools.fontBuilder import FontBuilder
        source=fitz.Font(fontbuffer=data);cff=CFFFontSet();cff.decompile(BytesIO(data),None);top=cff.topDictIndex[0];order=top.charset
        builder=FontBuilder(1000,isTTF=False);builder.setupGlyphOrder(order)
        builder.setupCharacterMap({cp:order[source.has_glyph(cp)] for cp in source.valid_codepoints() if 0<source.has_glyph(cp)<len(order)})
        from fontTools.pens.basePen import NullPen
        metrics={}
        for name in order:
            char=top.CharStrings[name];char.draw(NullPen());metrics[name]=(round(char.width),0)
        builder.setupHorizontalMetrics(metrics)
        builder.setupHorizontalHeader(ascent=round(source.ascender*1000),descent=round(source.descender*1000))
        bold=bool(source.flags.get('bold'));italic=bool(source.flags.get('italic'));style=('Bold' if bold else '')+('Italic' if italic else '') or 'Regular'
        builder.setupNameTable({'familyName':source.name,'styleName':style,'fullName':source.name,'psName':source.name})
        builder.setupOS2(usWeightClass=700 if bold else 400,fsSelection=(32 if bold else 0)|(1 if italic else 0)|(64 if not bold and not italic else 0),sTypoAscender=round(source.ascender*1000),sTypoDescender=round(source.descender*1000),usWinAscent=round(max(0,source.ascender)*1000),usWinDescent=round(max(0,-source.descender)*1000))
        builder.setupPost(italicAngle=-12 if italic else 0);font=builder.font;font['head'].macStyle=(1 if bold else 0)|(2 if italic else 0);font.sfntVersion='OTTO';font.recalcTimestamp=False;font['head'].created=2082844800;font['head'].modified=2082844800;table=newTable('CFF ');table.cff=cff;font['CFF ']=table;builder.setupMaxp()
    from fontTools.fontBuilder import FontBuilder
    builder=FontBuilder(font=font)
    if 'name' not in font:builder.setupNameTable({'familyName':'PDFEmbedded','styleName':'Regular','fullName':'PDFEmbedded','psName':'PDFEmbedded'})
    if 'OS/2' not in font:builder.setupOS2(sTypoAscender=font['hhea'].ascent,sTypoDescender=font['hhea'].descent,usWinAscent=max(0,font['hhea'].ascent),usWinDescent=max(0,-font['hhea'].descent))
    if 'post' not in font:builder.setupPost(keepGlyphNames=False)
    family='YoonDF_'+hashlib.sha256(data).hexdigest()[:18]
    # Exact program and style; unique family ensures loaded subsets never shadow each other.
    for record in list(font['name'].names):
        if record.nameID in (1,16,21):font['name'].setName(family,record.nameID,record.platformID,record.platEncID,record.langID)
    for nid in (1,16):font['name'].setName(family,nid,3,1,0x409)
    out=BytesIO();font.save(out);font.close();return out.getvalue(),family
