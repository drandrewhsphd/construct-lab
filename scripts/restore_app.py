import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from construct_lab.backup import list_backups,restore_backup
DB=ROOT/'data'/'construct-lab.sqlite'
try:
 # Older prototype servers predate database locks. Refuse recovery while one responds.
 import json
 from urllib.request import urlopen
 for port in range(8765,8781):
  active=False
  try:
   with urlopen(f'http://127.0.0.1:{port}/api/state',timeout=.3) as response:
    state=json.load(response);active=isinstance(state,dict) and 'projects' in state
  except Exception:pass
  if active:raise ValueError(f'A Construct Lab server is still running on port {port}. Stop it, or restart the computer and run Restore before opening the app.')
 choices=list_backups(DB)
 if not choices:raise ValueError('No backups found in data/backups.')
 for i,b in enumerate(choices,1):print(f"{i}. {b['filename']} - {b['projects']} projects, {b['pdfs']} PDFs")
 index=int(input('Backup number to restore: '))-1
 if not 0<=index<len(choices):raise ValueError('Invalid selection')
 print('This replaces all current projects. A safety backup will be saved first.')
 if input('Type RESTORE to continue: ')!='RESTORE':raise ValueError('Restore cancelled; no records changed.')
 result=restore_backup(DB,DB.parent/'backups'/choices[index]['filename'])
 print('Restore verified. Open Construct Lab.command to restart.')
 if result['safety_backup']:print('Previous state saved as '+result['safety_backup']['filename'])
except Exception as e:print('Recovery stopped: '+str(e))
input('Press Enter to close.')
