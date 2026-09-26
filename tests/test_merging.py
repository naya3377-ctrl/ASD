"""Merge actual PDFs, preserving source content and link destinations.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
from queue import Queue
from threading import Event
import tempfile
import unittest
import fitz
from bichaek.merging import inspect_source,merge_files


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.a=self.root/'a.pdf';self.b=self.root/'b.pdf'
        for path,count,label in [(self.a,2,'A'),(self.b,3,'B')]:
            pdf=fitz.open()
            for i in range(count):
                p=pdf.new_page(width=600 if i%2==0 else 800,height=800 if i%2==0 else 600)
                p.insert_text((40,80),f'{label}{i+1}',fontsize=24)
            p=pdf[0]
            p.insert_link({'kind':fitz.LINK_GOTO,'from':fitz.Rect(40,50,150,90),'page':count-1,'to':fitz.Point(0,0)})
            p.insert_link({'kind':fitz.LINK_URI,'from':fitz.Rect(40,100,150,120),'uri':'https://example.com'})
            p.add_text_annot((200,200),'Keep note').update()
            field=fitz.Widget();field.field_type=fitz.PDF_WIDGET_TYPE_TEXT;field.field_name='repeated';field.field_value=label;field.rect=fitz.Rect(40,300,240,330);p.add_widget(field)
            pdf.set_toc([[1,label+' contents',1],[2,'Last page',count]])
            pdf.save(path);pdf.close()
        self.original=[self.a.read_bytes(),self.b.read_bytes()]
    def tearDown(self):self.temp.cleanup()
    def run_merge(self,items=None,target=None,cancel=None):
        events=Queue();target=target or self.root/'joined.pdf'
        items=items or [{'path':str(self.b),'name':'b.pdf'},{'path':str(self.a),'name':'a.pdf'}]
        merge_files(items,str(target),str(self.root/'pending.pdf'),events,cancel or Event())
        output=[]
        while not events.empty():output.append(events.get())
        return target,output
    def test_order_links_notes_forms_bookmarks_and_originals(self):
        target,events=self.run_merge()
        self.assertTrue(events[-1].get('done'),events)
        with fitz.open(target) as pdf:
            self.assertEqual(len(pdf),5)
            self.assertEqual([p.get_text().splitlines()[0] for p in pdf],['B1','B2','B3','A1','A2'])
            self.assertEqual(pdf[0].get_links()[0]['page'],2)
            self.assertEqual(pdf[3].get_links()[0]['page'],4)
            self.assertEqual(pdf[3].get_links()[1]['uri'],'https://example.com')
            self.assertEqual(next(pdf[3].annots()).info['content'],'Keep note')
            self.assertEqual([next(pdf[x].widgets()).field_value for x in [0,3]],['B','A'])
            self.assertEqual([row[2] for row in pdf.get_toc() if row[0]==1],[1,4])
        self.assertEqual([self.a.read_bytes(),self.b.read_bytes()],self.original)
    def test_cancel_and_bad_source_do_not_replace_existing_output(self):
        target=self.root/'existing.pdf';target.write_bytes(self.original[0])
        cancel=Event();cancel.set();_,events=self.run_merge(target=target,cancel=cancel)
        self.assertTrue(events[-1].get('cancelled'));self.assertEqual(target.read_bytes(),self.original[0])
        items=[{'path':str(self.a),'name':'a'},{'path':str(self.root/'missing.pdf'),'name':'missing'}]
        _,events=self.run_merge(items,target)
        self.assertIn('error',events[-1]);self.assertEqual(target.read_bytes(),self.original[0])
        self.assertFalse((self.root/'pending.pdf').exists())
    def test_output_cannot_overwrite_input(self):
        _,events=self.run_merge(target=self.a)
        self.assertIn('error',events[-1]);self.assertEqual(self.a.read_bytes(),self.original[0])
    def test_encrypted_source_password_and_permissions(self):
        path=self.root/'encrypted.pdf'
        # Independently encrypted fixture; reader/owner passwords are test data.
        path.write_bytes((Path(__file__).parent/'fixtures/merge-encrypted.pdf').read_bytes())
        self.assertTrue(inspect_source(str(path)).get('passwordRequired'))
        with self.assertRaises(ValueError):inspect_source(str(path),'reader')
        info=inspect_source(str(path),'owner');self.assertEqual(info['count'],2);self.assertTrue(info['preview'].startswith(b'\x89PNG'))
        target,events=self.run_merge([{'path':str(path),'password':'owner','name':'encrypted'},{'path':str(self.b),'name':'b'}])
        self.assertTrue(events[-1].get('done'),events)
        with fitz.open(target) as pdf:self.assertIn('A1',pdf[0].get_text())

if __name__=='__main__':unittest.main()
