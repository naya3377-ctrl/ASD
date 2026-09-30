"""Run each UI regression in its own process with the production control style.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from pathlib import Path
import json, os, signal, subprocess, sys, time


def main():
    root=Path(__file__).resolve().parent.parent
    out=root/'test-output'/'qa';out.mkdir(parents=True,exist_ok=True)
    results=[]
    for script in sorted((root/'scripts').glob('qa_*.py')):
        env=dict(os.environ,QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',
                 YOONDF_QA_STYLE='YoonDF',QML_IMPORT_PATH=str(root/'ui/style'),
                 XDG_CONFIG_HOME=str(out/script.stem/'config'),XDG_CACHE_HOME=str(out/script.stem/'cache'))
        began=time.monotonic();log=out/(script.stem+'.log')
        with log.open('w',encoding='utf-8') as output:
            child=subprocess.Popen([sys.executable,str(script)],cwd=root,env=env,
                stdout=output,stderr=subprocess.STDOUT,start_new_session=os.name!='nt')
            try: code=child.wait(timeout=240)
            except subprocess.TimeoutExpired:
                if os.name=='nt': subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
                else: os.killpg(child.pid,signal.SIGKILL)
                child.wait();code=124
        result={'script':script.name,'exit':code,'seconds':round(time.monotonic()-began,2),
                'skipped':'SKIP:' in log.read_text(encoding='utf-8',errors='replace')}
        results.append(result);(out/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        print(json.dumps(result),flush=True)
    return int(any(item['exit'] for item in results))

if __name__=='__main__':sys.exit(main())
