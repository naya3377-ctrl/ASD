"""Movable native image objects; all transforms remain inside the saved PDF.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import re
import uuid
import fitz

NUMBER = rb'[+-]?(?:\d+(?:\.\d*)?|\.\d+)'
SINGLE_IMAGE = re.compile(rb'\s*q\s+(' + rb'\s+'.join([NUMBER]*6) + rb')\s+cm\s+/([A-Za-z0-9_.-]+)\s+Do\s+Q\s*')


def pdf_array(values): return '['+' '.join(format(float(x),'.9g') for x in values)+']'


class ImageObjectOperations:
    def _local_resources(self, page):
        """Copy both resource dictionaries before changing a per-page binding."""
        def copied(kind, value):
            if kind == 'xref': value = self.pdf.xref_object(int(value.split()[0]), compressed=True)
            if kind == 'null': value = '<<>>'
            xref = self.pdf.get_new_xref(); self.pdf.update_object(xref, value)
            return xref
        kind, value = self.pdf.xref_get_key(page.xref, 'Resources')
        if kind == 'null':
            # Page resources may be inherited from the page tree.
            parent = page.xref
            while kind == 'null':
                pk, pv = self.pdf.xref_get_key(parent, 'Parent')
                if pk != 'xref': break
                parent = int(pv.split()[0]); kind, value = self.pdf.xref_get_key(parent, 'Resources')
        resources = copied(kind, value)
        xobjects = copied(*self.pdf.xref_get_key(resources, 'XObject'))
        self.pdf.xref_set_key(resources, 'XObject', f'{xobjects} 0 R')
        self.pdf.xref_set_key(page.xref, 'Resources', f'{resources} 0 R')
        return xobjects

    def _image_form(self, page, stream):
        data = self.pdf.xref_stream(stream)
        match = SINGLE_IMAGE.fullmatch(data)
        if not match: raise ValueError('이 이미지의 구조는 직접 이동을 지원하지 않아요.')
        matrix = fitz.Matrix(*map(float, match[1].split()))
        resource = match[2].decode('ascii')
        ref = next(i[0] for i in page.get_images() if i[7] == resource)
        bounds = fitz.Rect(0,0,1,1) * matrix
        form = self.pdf.get_new_xref()
        self.pdf.update_object(form, f'<</Type/XObject/Subtype/Form/FormType 1/BBox {pdf_array(bounds)} '
            f'/Resources<</XObject<</{resource} {ref} 0 R>>>>/YoonDFImage ({uuid.uuid4().hex})>>')
        self.pdf.update_stream(form, data)
        name = 'YDImage'+uuid.uuid4().hex
        xobjects = self._local_resources(page)
        self.pdf.xref_set_key(xobjects, name, f'{form} 0 R')
        self.pdf.update_stream(stream, f'q /{name} Do Q'.encode('ascii'))
        return name, form

    def movable_images(self, page):
        p = self.pdf[page]
        items = []
        for xref, name, invoker, bounds in p.get_xobjects():
            if invoker or self.pdf.xref_get_key(xref,'YoonDFImage')[0] != 'string': continue
            rect = fitz.Rect(bounds) * p.transformation_matrix * p.rotation_matrix
            if rect.is_empty: continue
            items.append({'id':str(xref), 'resource':name, 'rect':list(rect), 'page':page,
                          'session':self.session, 'revision':self.revision, 'legacy':False})
        # Recognize isolated image streams produced by older YoonDF versions.
        infos = None
        for stream in p.get_contents():
            match = SINGLE_IMAGE.fullmatch(self.pdf.xref_stream(stream))
            if not match: continue
            if infos is None: infos = p.get_image_info()
            matrix = fitz.Matrix(*map(float,match[1].split()))
            expected = fitz.Matrix(1,0,0,-1,0,1) * matrix * p.transformation_matrix
            matches = [i for i in infos if all(abs(a-b)<.01 for a,b in zip(i['transform'],expected))]
            if len(matches) != 1: continue
            rect = fitz.Rect(matches[0]['bbox']) * p.rotation_matrix
            items.append({'id':'stream:'+str(stream), 'resource':'', 'rect':list(rect), 'page':page,
                          'session':self.session, 'revision':self.revision, 'legacy':True})
        return items

    def transform_image(self, page, identifier, rect, session, revision):
        self.require()
        if session != self.session or revision != self.revision:
            raise ValueError('문서가 변경되었어요. 이미지를 다시 선택해 주세요.')
        item = next((i for i in self.movable_images(page) if i['id']==identifier), None)
        if not item: raise ValueError('선택한 이미지를 이동할 수 없어요.')
        p = self.pdf[page]
        display = fitz.Rect(rect)
        if display.is_empty or not all(__import__('math').isfinite(v) for v in display):
            raise ValueError('이미지 위치가 올바르지 않아요.')
        if display.width<8 or display.height<8 or not p.rect.contains(display):
            raise ValueError('이미지를 페이지 안에 놓고 크기를 8pt 이상으로 지정해 주세요.')
        old = fitz.Rect(item['rect']) * p.derotation_matrix
        new = display * p.derotation_matrix
        sx, sy = new.width/old.width, new.height/old.height
        native = fitz.Matrix(sx,0,0,sy,new.x0-old.x0*sx,new.y0-old.y0*sy)
        delta = p.transformation_matrix * native * ~p.transformation_matrix
        with self.transaction():
            p = self.pdf[page]
            if item['legacy']:
                name, form = self._image_form(p, int(identifier.split(':')[1]))
            else: name, form = item['resource'], int(identifier)
            # Cloning prevents changes to duplicated pages or shared imported forms.
            copied = self.pdf.get_new_xref();self.pdf.update_object(copied,'<<>>')
            self.pdf.xref_copy(form,copied)
            # xref_copy in PyMuPDF 1.26.6 does not quote custom string values.
            tag = self.pdf.xref_get_key(form, 'YoonDFImage')[1]
            self.pdf.xref_set_key(copied, 'YoonDFImage', fitz.get_pdf_str(tag))
            kind, value = self.pdf.xref_get_key(copied,'Matrix')
            matrix = fitz.Matrix(*map(float,value.strip('[]').split())) if kind=='array' else fitz.Matrix(1,0,0,1,0,0)
            self.pdf.xref_set_key(copied,'Matrix',pdf_array(matrix*delta))
            self.pdf.xref_set_key(self._local_resources(p),name,f'{copied} 0 R')
        result=self.info();result['imageFocus']={'page':page,'id':str(copied)}
        return result
