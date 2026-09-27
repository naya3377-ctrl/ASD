"""Lossless ordered PDF joining with atomic output and cancellable progress.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import os
import fitz


def open_source(path,password=''):
    pdf=fitz.open(path)
    if not pdf.is_pdf or not len(pdf):
        pdf.close();raise ValueError('페이지가 있는 PDF 파일을 선택해 주세요.')
    encrypted=pdf.needs_pass
    authenticated=pdf.authenticate(password) if encrypted else 0
    if encrypted and not authenticated:
        pdf.close();return None
    if not (authenticated & 4) and not pdf.permissions & fitz.PDF_PERM_ASSEMBLE:
        pdf.close();raise ValueError('이 PDF는 결합 권한이 제한되어 있어요. 소유자 암호가 필요합니다.')
    return pdf


def inspect_source(path,password=''):
    pdf=open_source(path,password)
    if pdf is None:return {'passwordRequired':True}
    try:
        page=pdf[0];scale=min(180/page.rect.width,242/page.rect.height)
        pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
        return {'name':Path(path).name,'path':str(Path(path).resolve()),'count':len(pdf),
                'bytes':Path(path).stat().st_size,'preview':pix.tobytes('png')}
    finally:pdf.close()


def merge_files(items,target,temp_path,events,cancel):
    """Never replace an input. Keep every source's internal links in one insert."""
    output=None
    try:
        destination=Path(target).resolve()
        for item in items:
            for value in [item['path'],item.get('originalPath',item['path'])]:
                source=Path(value).resolve()
                if source==destination or (destination.exists() and os.path.samefile(source,destination)):
                    raise ValueError('원본과 다른 이름으로 결합 파일을 저장해 주세요.')
        if len(items)<2:raise ValueError('결합할 PDF를 두 개 이상 추가해 주세요.')
        output=fitz.open();bookmarks=[];total=0
        for index,item in enumerate(items):
            if cancel.is_set():events.put({'cancelled':True});return
            source=open_source(item['path'],item.get('password',''))
            if source is None:raise ValueError(item['name']+': PDF 암호를 확인해 주세요.')
            try:
                offset=len(output)
                # Chunking insert_pdf drops destinations outside each chunk.
                # Keep each complete source together to preserve internal links.
                output.insert_pdf(source,links=True,annots=True,widgets=True)
                bookmarks.append([1,item['name'],offset+1])
                previous=1
                for level,title,page in source.get_toc():
                    if page<1:continue
                    depth=min(level+1,previous+1)
                    bookmarks.append([depth,title,page+offset]);previous=depth
                total+=len(source)
            finally:source.close()
            events.put({'progress':index+1,'total':len(items),'pages':total})
        if cancel.is_set():events.put({'cancelled':True});return
        output.set_toc(bookmarks)
        output.set_metadata({'title':destination.stem,'creator':'YoonDF 0.9.8'})
        output.save(temp_path,garbage=3,deflate=True)
        output.close();output=None
        with fitz.open(temp_path) as verify:
            if len(verify)!=total:raise ValueError('결합된 PDF의 페이지 수 검증에 실패했어요.')
        if cancel.is_set():events.put({'cancelled':True});return
        os.replace(temp_path,destination)
        events.put({'done':True,'path':str(destination),'pages':total})
    except Exception as exc:events.put({'error':str(exc)})
    finally:
        if output:output.close()
        Path(temp_path).unlink(missing_ok=True)
