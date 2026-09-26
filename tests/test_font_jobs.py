"""Hung font subprocesses must not own or destroy the document."""
from pathlib import Path
import tempfile,subprocess,time,unittest,threading,multiprocessing
from unittest.mock import patch
from bichaek import font_jobs

class FontJobTests(unittest.TestCase):
    def test_actual_hung_child_is_killed_and_next_request_works(self):
        real=subprocess.Popen
        children=[]
        def hanging(args,**kwargs):
            child=real([args[0],'-c','import time;time.sleep(30)'],**kwargs)
            children.append(child)
            return child
        started=time.monotonic()
        with patch.object(font_jobs.subprocess,'Popen',side_effect=hanging):
            with self.assertRaisesRegex(ValueError,'초과'):font_jobs.run_job({'operation':'list'},timeout=.2)
        self.assertLess(time.monotonic()-started,3)
        self.assertIsNotNone(children[0].poll())
        result=font_jobs.run_job({'operation':'list'})
        self.assertIsInstance(result['fonts'],list)

    def test_shutdown_signal_reaps_font_child_without_waiting_for_timeout(self):
        real=subprocess.Popen;children=[]
        cancel=multiprocessing.get_context('spawn').Event()
        def hanging(args,**kwargs):
            child=real([args[0],'-c','import time;time.sleep(30)'],**kwargs)
            children.append(child)
            return child
        timer=threading.Timer(.2,cancel.set);timer.start()
        try:
            started=time.monotonic()
            with patch.object(font_jobs,'CANCEL_EVENT',cancel), patch.object(font_jobs.subprocess,'Popen',side_effect=hanging):
                with self.assertRaisesRegex(ValueError,'종료'):font_jobs.run_job({'operation':'list'},timeout=15)
            self.assertLess(time.monotonic()-started,3)
            self.assertIsNotNone(children[0].poll())
        finally:timer.cancel();timer.join()

if __name__=='__main__':unittest.main()
