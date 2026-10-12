"""Start/reopen the one supported local address. Never choose a new port silently."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen
import webbrowser
ROOT=Path(__file__).resolve().parents[1]
URL='http://127.0.0.1:8780'
def health():
 try:
  with urlopen(URL+'/api/health',timeout=1) as r:return json.load(r)
 except Exception:return None
if health()!=dict(app='construct-lab',build='research-loop-1'):
 if health() is not None:raise SystemExit('An older Construct Lab server is running. Stop it before opening the updated app.')
 sys.path.insert(0,str(ROOT/'src'))
 from construct_lab.backup import create_backup
 if (ROOT/'data'/'construct-lab.sqlite').exists():create_backup(ROOT/'data'/'construct-lab.sqlite')
 env=dict(os.environ,PYTHONPATH=str(ROOT/'src'))
 (ROOT/'data').mkdir(exist_ok=True)
 with (ROOT/'data'/'app-server.log').open('a') as log:
  child=subprocess.Popen([sys.executable,'-m','construct_lab.server','--database',str(ROOT/'data'/'construct-lab.sqlite'),'--port','8780'],cwd=ROOT,env=env,stdout=log,stderr=log,start_new_session=True)
 for _ in range(30):
  if child.poll() is not None:raise SystemExit('Construct Lab could not start on port 8780. Check data/app-server.log. No other server was stopped.')
  if health()==dict(app='construct-lab',build='research-loop-1'):break
  time.sleep(.2)
 else:raise SystemExit('The server did not become ready. Check data/app-server.log.')
print('Construct Lab: '+URL)
if '--no-browser' not in sys.argv:webbrowser.open(URL)
