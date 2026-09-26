"""Native PDF comments validated with an independent parser and foreign writer.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import tempfile
import unittest
import fitz
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (DictionaryObject,NameObject,ArrayObject,FloatObject,
                           NumberObject,TextStringObject,DecodedStreamObject)
from bichaek.document import Document,DocumentError


def array(values): return ArrayObject([FloatObject(x) for x in values])


def foreign_fixture(path):
    """Synthetic standard PDF made with pypdf, not an Acrobat execution claim."""
    writer=PdfWriter();page=writer.add_blank_page(width=600,height=800)
    page_ref=page.indirect_reference
    appearance=DecodedStreamObject()
    appearance.set_data(b'q 1 0.8 0 rg 0 0 180 20 re f Q')
    appearance.update({NameObject('/Type'):NameObject('/XObject'),NameObject('/Subtype'):NameObject('/Form'),
                       NameObject('/BBox'):array([0,0,180,20])})
    ap=writer._add_object(appearance)
    def annot(kind,name,rect,content,flags=4):
        value=DictionaryObject({NameObject('/Type'):NameObject('/Annot'),NameObject('/Subtype'):NameObject('/'+kind),
            NameObject('/Rect'):array(rect),NameObject('/NM'):TextStringObject(name),
            NameObject('/Contents'):TextStringObject(content),NameObject('/T'):TextStringObject('외부 검토자'),
            NameObject('/CreationDate'):TextStringObject("D:20250102030405+09'00'"),NameObject('/M'):TextStringObject("D:20250102040506+09'00'"),
            NameObject('/C'):array([1,.8,0]),NameObject('/F'):NumberObject(flags),NameObject('/P'):page_ref,
            NameObject('/AP'):DictionaryObject({NameObject('/N'):ap}),
            NameObject('/VendorData'):TextStringObject('preserve this custom field')})
        return writer._add_object(value)
    parent=annot('Highlight','foreign-markup',[50,600,230,620],'이전 내용')
    parent.get_object()[NameObject('/QuadPoints')]=array([50,620,230,620,50,600,230,600])
    parent.get_object()[NameObject('/RC')]=TextStringObject('<body><p>이전 내용</p></body>')
    popup=DictionaryObject({NameObject('/Type'):NameObject('/Annot'),NameObject('/Subtype'):NameObject('/Popup'),
        NameObject('/Rect'):array([240,600,450,720]),NameObject('/Parent'):parent,NameObject('/P'):page_ref})
    popup_ref=writer._add_object(popup);parent.get_object()[NameObject('/Popup')]=popup_ref
    reply=annot('Text','foreign-reply',[50,600,70,620],'외부 프로그램의 답글',56)
    reply.get_object()[NameObject('/IRT')]=parent;reply.get_object()[NameObject('/RT')]=NameObject('/R')
    locked=annot('Text','locked-comment',[70,300,90,320],'잠긴 메모',4|128)
    unsupported=annot('FreeText','foreign-free-text',[50,200,230,220],'서식 있는 텍스트')
    unsupported.get_object()[NameObject('/DA')]=TextStringObject('/Helv 11 Tf 0 g')
    state=annot('Text','review-state',[50,600,70,620],'',56)
    state.get_object()[NameObject('/IRT')]=parent
    state.get_object()[NameObject('/StateModel')]=TextStringObject('Review')
    state.get_object()[NameObject('/State')]=TextStringObject('Accepted')
    page[NameObject('/Annots')]=ArrayObject([parent,popup_ref,reply,locked,unsupported,state])
    with open(path,'wb') as stream: writer.write(stream)


class AnnotationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.path=self.root/'source.pdf'
        with fitz.open() as pdf:
            for rotation in (0,90,180,270):
                p=pdf.new_page(width=660,height=860)
                p.insert_text((80,140),'Alpha beta gamma',fontsize=20)
                p.insert_text((80,175),'Second line to comment',fontsize=20)
                p.set_cropbox(fitz.Rect(30,40,630,840));p.set_rotation(rotation)
            pdf.save(self.path)
        self.doc=Document();self.doc.open(str(self.path))

    def tearDown(self):self.doc.close();self.tmp.cleanup()

    def test_standard_objects_unicode_replies_and_nonflattened_pages(self):
        before=[self.doc.pdf[i].read_contents() for i in range(4)]
        for page,kind in enumerate(('highlight','underline','strikeout','squiggly')):
            layout=self.doc.text_layout(page)
            end=layout['lines'][1]['end']
            self.doc.add_markup(page,kind,0,end,author='한글 작성자',content='수정 검토 의견',color='#7dbbe6')
            item=self.doc.annotations_page(page)['items'][0]
            self.assertGreaterEqual(len(item['regions']),2)
            # Native quads agree with the rotated/cropped character geometry.
            first_char=fitz.Rect(layout['chars'][0][1:5])
            self.assertTrue(fitz.Rect(item['regions'][0]).intersects(first_char))
        self.doc.add_comment(0,[380,240],'한글 메모\n두 번째 줄',author='검토자')
        parent=self.doc.annotations_page(0)['items'][0]
        self.doc.reply_annotation(0,parent['id'],'답글입니다',author='동료',revision=self.doc.revision)
        target=self.root/'out.pdf';self.doc.save(str(target))
        reader=PdfReader(target);seen=set()
        for page in reader.pages:
            for ref in page['/Annots']:
                a=ref.get_object()
                if a['/Subtype']=='/Popup':continue
                seen.add(str(a['/Subtype']))
                self.assertTrue(a['/NM']);self.assertIn('/CreationDate',a);self.assertIn('/M',a)
                self.assertTrue(a['/AP']['/N'].get_object().get_data())
                self.assertIn('/T',a)
                if a['/Subtype']!='/Text':self.assertEqual(len(a['/QuadPoints'])%8,0)
                if '/IRT' in a:
                    self.assertEqual(a['/RT'],'/R');self.assertEqual(a['/IRT']['/NM'],parent['name'])
                    self.assertEqual(a['/Contents'],'답글입니다')
                    self.assertFalse(a['/F'] & 4)
        self.assertEqual(seen,{'/Highlight','/Underline','/StrikeOut','/Squiggly','/Text'})
        with fitz.open(target) as pdf:
            for i in range(4):self.assertEqual(before[i],pdf[i].read_contents())
        # Stable ID, native metadata and reply link survive reopen/save/undo.
        self.doc.open(str(target));items=self.doc.annotations_page(0)['items']
        self.assertTrue(any(x['author']=='동료' and x['parentId']==parent['id'] for x in items))
        self.doc.delete_annotation(0,parent['id'],revision=self.doc.revision)
        self.assertEqual(len(self.doc.annotations_page(0)['items']),1)
        self.doc.undo();self.assertEqual(len(self.doc.annotations_page(0)['items']),3)
        self.doc.redo();self.assertEqual(len(self.doc.annotations_page(0)['items']),1)

    def test_foreign_popup_rich_text_reply_appearance_and_unknown_preserved(self):
        source=self.root/'foreign.pdf';foreign_fixture(source)
        original=PdfReader(source)
        old={a.get_object().get('/NM'):a.get_object() for a in original.pages[0]['/Annots'] if a.get_object().get('/NM')}
        self.doc.open(str(source))
        items=self.doc.annotations_page(0)['items'];byname={x['name']:x for x in items}
        self.assertEqual(byname['foreign-reply']['parentId'],'nm:foreign-markup')
        for name in ('foreign-free-text','locked-comment','review-state'):self.assertFalse(byname[name]['editable'])
        target=byname['foreign-markup']
        self.doc.update_annotation(0,target['id'],'새로운 한글 의견','다른 작성자',revision=self.doc.revision)
        out=self.root/'foreign-updated.pdf';self.doc.save(str(out))
        new={a.get_object().get('/NM'):a.get_object() for a in PdfReader(out).pages[0]['/Annots'] if a.get_object().get('/NM')}
        a=new['foreign-markup'];self.assertEqual(a['/Contents'],'새로운 한글 의견');self.assertEqual(a['/T'],'다른 작성자')
        self.assertTrue('/RC' not in a or a['/RC'] is None or str(a['/RC'])=='NullObject')
        self.assertEqual(a['/CreationDate'],old['foreign-markup']['/CreationDate'])
        self.assertEqual(a['/AP']['/N'].get_object().get_data(),old['foreign-markup']['/AP']['/N'].get_object().get_data())
        self.assertEqual(a['/Popup']['/Parent']['/NM'],'foreign-markup')
        for name in ('foreign-reply','foreign-free-text','locked-comment','review-state'):
            for key in ('/Contents','/T','/C','/F','/VendorData'):
                self.assertEqual(new[name][key],old[name][key])
            self.assertEqual(new[name]['/AP']['/N'].get_object().get_data(),old[name]['/AP']['/N'].get_object().get_data())
        self.assertEqual(new['review-state']['/State'],'Accepted')
        self.assertEqual(new['review-state']['/IRT']['/NM'],'foreign-markup')

    def test_annotation_only_permissions_and_locked_objects(self):
        secured=self.root/'comments-only.pdf'
        with fitz.open(self.path) as pdf:
            pdf.save(secured,encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='reader',
                     permissions=fitz.PDF_PERM_ANNOTATE|fitz.PDF_PERM_COPY|fitz.PDF_PERM_PRINT)
        self.doc.open(str(secured),'reader')
        self.assertFalse(self.doc.editable());self.assertTrue(self.doc.annotatable())
        self.doc.add_comment(0,[50,60],'주석 허용')
        self.doc.add_markup(0,'underline',0,5)
        with self.assertRaises(DocumentError):self.doc.rotate([0])
        denied=self.root/'no-comments.pdf'
        with fitz.open(self.path) as pdf:pdf.save(denied,encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='reader',permissions=fitz.PDF_PERM_PRINT)
        self.doc.open(str(denied),'reader')
        with self.assertRaises(DocumentError):self.doc.add_comment(0,[50,60],'허용되지 않음')
        source=self.root/'foreign.pdf';foreign_fixture(source);self.doc.open(str(source))
        with self.assertRaises(ValueError):self.doc.update_annotation(0,'nm:locked-comment','x','y',revision=self.doc.revision)
        with self.assertRaises(ValueError):self.doc.delete_annotation(0,'nm:locked-comment',revision=self.doc.revision)
        # A parent with a read-only review-state child must not erase that child.
        with self.assertRaises(ValueError):self.doc.delete_annotation(0,'nm:foreign-markup',revision=self.doc.revision)
        self.assertFalse(self.doc.info()['dirty'])

    def test_stale_targets_color_change_and_save_handle_invalidation(self):
        self.doc.add_comment(0,[50,60],'first')
        a=self.doc.annotations_page(0)['items'][0];revision=self.doc.revision
        self.doc.update_annotation(0,a['id'],'second','A',color='#ef9bc0',revision=revision)
        self.assertEqual(self.doc.annotations_page(0)['items'][0]['color'],'#ef9bc0')
        with self.assertRaises(ValueError):self.doc.reply_annotation(0,a['id'],'stale',revision=revision)
        revision=self.doc.revision;self.doc.save(str(self.root/'new.pdf'))
        self.assertGreater(self.doc.revision,revision)
        with self.assertRaises(ValueError):self.doc.update_annotation(0,a['id'],'stale','A',revision=revision)
        with self.assertRaises(ValueError):self.doc.add_markup(0,'highlight',100000,100004)

if __name__=='__main__':unittest.main()
