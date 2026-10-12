"""User-invoked restart of this workspace's verified local server only."""
import json,os,signal,subprocess,sys,time
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
try:
 try:
  with urlopen('http://127.0.0.1:8780/api/health',timeout=2) as r:health=json.load(r)
 except Exception:health=None
 if health:
  if health.get('app')!='construct-lab':raise ValueError('Port 8780 belongs to another application; restart cancelled.')
  output=subprocess.check_output(['/usr/sbin/lsof','-t','-iTCP:8780','-sTCP:LISTEN'],text=True)
  pids=set(output.split())
  if len(pids)!=1:raise ValueError('Could not uniquely identify the app server.')
  pid=int(pids.pop())
  cwd=subprocess.check_output(['/usr/sbin/lsof','-a','-p',str(pid),'-d','cwd','-Fn'],text=True)
  if 'n'+str(ROOT) not in cwd.splitlines():raise ValueError('Server belongs to a different workspace; restart cancelled.')
  sys.path.insert(0,str(ROOT/'src'))
  from construct_lab.backup import create_backup
  create_backup(ROOT/'data'/'construct-lab.sqlite')
  os.kill(pid,signal.SIGTERM)
  for _ in range(50):
   try:os.kill(pid,0)
   except ProcessLookupError:break
   time.sleep(.1)
  else:raise ValueError('Server did not stop. No forced termination was attempted.')
 subprocess.run([sys.executable,str(ROOT/'scripts'/'launch_app.py')],cwd=ROOT,check=True)
except Exception as e:
 print('Restart could not finish: '+str(e));input('Press Enter to close.')
