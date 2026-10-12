"""Load the bundled demonstration; never overwrite an existing project."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from construct_lab.etymology import EtymologyStore
from construct_lab.backup import acquire_lock
p=argparse.ArgumentParser();p.add_argument('--database',default=str(ROOT/'data/construct-lab.sqlite'));a=p.parse_args()
path=Path(a.database);path.parent.mkdir(parents=True,exist_ok=True)
lock=acquire_lock(path)
try:
 data=json.loads((ROOT/'examples/immersiveness-demo.json').read_text())
 store=EtymologyStore(path)
 if store.db.execute('SELECT 1 FROM projects WHERE id=?',(data['project'],)).fetchone():
  print('Demonstration already present. No changes made.')
 else:
  with store.db:
   store.db.execute('INSERT INTO projects(id,name,version) VALUES (?,?,0)',(data['project'],data['name']))
   for table,key,fields in [('etymology_records','records',['id','project','kind','version','content','links']),('etymology_history','history',['id','record','version','content','links','actor','reason','created_at'])]:
    for row in data[key]:
     store.db.execute('INSERT INTO '+table+' ('+','.join(fields)+') VALUES ('+','.join('?' for _ in fields)+')',[row[f] for f in fields])
  print('Loaded immersiveness demonstration. Synthetic cases and observations are not empirical findings.')
 store.db.close()
finally:lock.close()
