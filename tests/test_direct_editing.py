"""Persistent object placement and multi-page moves, including undo and shared resources.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import tempfile
import unittest
import fitz
from bichaek.document import Document


class DirectEditingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.path=self.root/'source.pdf';self.png=self.root/'image.png'
        pix=fitz.Pixmap(fitz.csRGB,fitz.IRect(0,0,100,50),False);pix.clear_with(100);pix.save(self.png)
        with fitz.open() as pdf:
            for i in range(6):
                p=pdf.new_page(width=600,height=800);p.insert_text((40,60),f'PAGE {i+1}')
            pdf[0].insert_link({'kind':fitz.LINK_GOTO,'from':fitz.Rect(40,80,150,100),'page':4})
            pdf.set_toc([[1,'Chapter Five',5]])
            pdf.save(self.path)
        self.doc=Document();self.doc.open(str(self.path))
    def tearDown(self):self.doc.close();self.temp.cleanup()
    def transform(self,item,rect):
        return self.doc.transform_image(item['page'],item['id'],rect,item['session'],item['revision'])
    def close_rect(self,a,b):
        for x,y in zip(a,b):self.assertAlmostEqual(x,y,places=2)
    def test_image_move_resize_save_reopen_rotation_and_body_edit(self):
        for rotation in [0,90,180,270]:
            self.doc.open(str(self.path));self.doc.rotate([0],rotation)
            self.doc.add_image(0,[80,150,280,250],str(self.png))
            item=self.doc.movable_images(0)[0]
            self.close_rect(item['rect'],[80,150,280,250])
            self.transform(item,[130,210,430,360])
            item=self.doc.movable_images(0)[0];self.close_rect(item['rect'],[130,210,430,360])
            with self.assertRaises(ValueError):self.transform(item,[-1,2,100,100])
            block=self.doc.objects(0)['blocks'][0]
            self.doc.replace_text(0,block['id'],'EDIT 1',11,height=40)
            item=self.doc.movable_images(0)[0]
            self.transform(item,[140,220,440,370])
            saved=self.root/f'image-{rotation}.pdf';self.doc.save(str(saved));self.doc.open(str(saved))
            item=self.doc.movable_images(0)[0];self.close_rect(item['rect'],[140,220,440,370])
            info=self.doc.pdf[0].get_image_info()[0]
            self.close_rect(fitz.Rect(info['bbox'])*self.doc.pdf[0].rotation_matrix,[140,220,440,370])
            self.transform(item,[50,250,250,350]);self.doc.undo()
            self.close_rect(self.doc.movable_images(0)[0]['rect'],[140,220,440,370])
            self.doc.redo();self.close_rect(self.doc.movable_images(0)[0]['rect'],[50,250,250,350])
    def test_legacy_isolated_image_and_shared_form_are_independent(self):
        self.doc.pdf[0].insert_image([100,150,300,250],filename=str(self.png))
        item=self.doc.movable_images(0)[0];self.assertTrue(item['legacy'])
        self.transform(item,[130,190,330,290])
        self.doc.pdf.fullcopy_page(0,to=1)
        first=self.doc.movable_images(0)[0];second=self.doc.movable_images(1)[0]
        self.transform(first,[200,400,400,500])
        self.close_rect(self.doc.movable_images(1)[0]['rect'],second['rect'])
        self.assertEqual(len(self.doc.pdf[0].get_image_info()),1)
    def test_cropbox_image_move(self):
        p=self.doc.pdf[0];p.set_cropbox(fitz.Rect(20,30,580,770))
        self.doc.add_image(0,[100,150,300,250],str(self.png))
        item=self.doc.movable_images(0)[0];self.close_rect(item['rect'],[100,150,300,250])
        self.transform(item,[150,200,350,300])
        self.close_rect(self.doc.pdf[0].get_image_info()[0]['bbox'],[150,200,350,300])
    def test_memo_moves_independently_retains_reply_and_undo(self):
        self.doc.add_comment(0,[100,150],'메모 내용',author='작성자')
        note=self.doc.annotations_page(0)['items'][0]
        self.doc.reply_annotation(0,note['id'],'답글','다른 작성자',revision=self.doc.revision)
        note=self.doc.annotations_page(0)['items'][0]
        self.doc.move_annotation(0,note['id'],[330,420],self.doc.session,self.doc.revision)
        items=self.doc.annotations_page(0)['items'];self.close_rect(items[0]['rect'][:2],[330,420])
        self.assertEqual(items[0]['content'],'메모 내용');self.assertEqual(items[1]['parentId'],items[0]['id'])
        self.doc.undo();self.close_rect(self.doc.annotations_page(0)['items'][0]['rect'],note['rect'])
        self.doc.redo();saved=self.root/'notes.pdf';self.doc.save(str(saved))
        with fitz.open(saved) as pdf:
            annots=list(pdf[0].annots());self.assertEqual(len(annots),2)
        for turn in range(1,4):
            self.doc.rotate([0],90);note=self.doc.annotations_page(0)['items'][0]
            self.doc.move_annotation(0,note['id'],[220,150],self.doc.session,self.doc.revision)
            self.close_rect(self.doc.annotations_page(0)['items'][0]['rect'][:2],[220,150])
            self.assertEqual(self.doc.annotations_page(0)['items'][1]['parentId'],note['id'])
    def test_multi_page_move_preserves_links_bookmarks_and_one_undo(self):
        before=[p.xref for p in self.doc.pdf]
        result=self.doc.move_pages([1,3],6,revision=self.doc.revision)
        self.assertEqual(result['movedSelection'],[4,5])
        self.assertEqual([p.xref for p in self.doc.pdf],[before[i] for i in [0,2,4,5,1,3]])
        self.assertEqual(self.doc.pdf[0].get_links()[0]['page'],2)
        self.assertEqual(self.doc.pdf.get_toc()[0][2],3)
        self.doc.undo();self.assertEqual([p.xref for p in self.doc.pdf],before)
        self.doc.move_pages([3,4],0);self.assertEqual(self.doc.pdf[0].get_text().strip(),'PAGE 4')
        self.doc.undo();self.doc.move_pages(list(range(6)),3)
        self.assertEqual([p.xref for p in self.doc.pdf],before)

if __name__=='__main__':unittest.main()
