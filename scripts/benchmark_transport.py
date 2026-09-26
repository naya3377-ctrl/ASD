"""Compare old PNG IPC with display-list + shared memory IPC, including QImage decode/copy."""
from pathlib import Path
import os,sys,time,json,statistics,importlib.util,multiprocessing as mp
from multiprocessing.shared_memory import SharedMemory
ROOT=Path(__file__).resolve().parent.parent
BASELINE=Path(os.environ.get('BICHAEK_BASELINE',str(ROOT/'benchmarks/baseline_020')))
sys.path.insert(0,str(ROOT))

def worker(conn,mode,path,shared):
    if mode=='old':
        spec=importlib.util.spec_from_file_location('baseline_doc',BASELINE/'bichaek/document.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);Document=mod.Document
    else:
        from bichaek.document import Document
    doc=Document();doc.open(path);conn.send('ready')
    try:
        while True:
            request=conn.recv()
            if request is None:return
            page,width=request
            result=doc.render(page,width) if mode=='old' else doc.render_frame(page,width,shared)
            conn.send(result)
    finally:doc.close()

def main():
    from PySide6.QtGui import QImage
    ctx=mp.get_context('spawn');frame=SharedMemory(create=True,size=48_065_536)
    data={}
    try:
        for mode in ['old','new']:
            parent,child=ctx.Pipe();process=ctx.Process(target=worker,args=(child,mode,str(ROOT/'samples/sample.pdf'),frame.name));process.start();parent.recv()
            rows=[]
            for page,width in [(0,1600),(3,1600),(0,3000),(3,3000)]:
                times=[]
                for repeat in range(7):
                    begin=time.perf_counter();parent.send((page,width));result=parent.recv()
                    if mode=='old':image=QImage.fromData(result['png'],'PNG')
                    else:image=QImage(frame.buf,result['width'],result['height'],result['stride'],QImage.Format_RGB888).copy()
                    assert not image.isNull();del image
                    elapsed=(time.perf_counter()-begin)*1000
                    if repeat:times.append(elapsed)
                rows.append({'page':page+1,'width':width,'median_ms':round(statistics.median(times),2)})
            data[mode]=rows;parent.send(None);process.join(5)
        print(json.dumps(data,indent=2))
        (ROOT/'benchmarks/transport-results.json').write_text(json.dumps(data,indent=2))
    finally:frame.close();frame.unlink()
if __name__=='__main__':main()
