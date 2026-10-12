"""Verified SQLite backups and offline recovery, including original PDF blobs."""
import fcntl
import hashlib
import json
import sqlite3
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4


def readonly(path):return sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
def verify(path):
 with readonly(path) as db:
  if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Database integrity check failed')
  tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  if not {'projects','documents','passages','revisions'}.issubset(tables):raise ValueError('Not a complete Construct Lab database')
  return dict(projects=db.execute('SELECT count(*) FROM projects').fetchone()[0],pdfs=db.execute('SELECT count(*) FROM documents').fetchone()[0])
def create_backup(database):
 database=Path(database).resolve();directory=database.parent/'backups';directory.mkdir(exist_ok=True)
 name='construct-lab-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:8]+'.sqlite'
 path=directory/name
 try:
  with readonly(database) as source,sqlite3.connect(path) as target:source.backup(target)
  counts=verify(path);digest=hashlib.sha256(path.read_bytes()).hexdigest()
  meta=dict(filename=name,created_at=datetime.now(timezone.utc).isoformat(),sha256=digest,bytes=path.stat().st_size,**counts)
  path.with_suffix('.json').write_text(json.dumps(meta,indent=2));path.chmod(0o600)
  return meta
 except Exception:
  path.unlink(missing_ok=True);raise

def list_backups(database):
 result=[]
 for p in (Path(database).parent/'backups').glob('*.json'):
  try:
   item=json.loads(p.read_text())
   if p.with_suffix('.sqlite').is_file():result.append(item)
  except (ValueError,OSError):continue
 return sorted(result,key=lambda x:x['created_at'],reverse=True)

def acquire_lock(database):
 f=open(str(Path(database).resolve())+'.server-lock','a')
 try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:
  f.close();raise ValueError('Construct Lab is running. Stop the app before restoring or starting another server.') from None
 return f

def restore_backup(database,source):
 database=Path(database).resolve();source=Path(source).resolve()
 if database==source:raise ValueError('Choose a backup, not the active database')
 verify(source)
 metadata=source.with_suffix('.json')
 if metadata.exists() and hashlib.sha256(source.read_bytes()).hexdigest()!=json.loads(metadata.read_text())['sha256']:raise ValueError('Backup checksum mismatch; restore cancelled')
 lock=acquire_lock(database)
 try:
  safety=create_backup(database) if database.exists() else None
  with readonly(source) as src,sqlite3.connect(database) as dst:src.backup(dst)
  verify(database)
  return dict(restored=str(source),safety_backup=safety)
 finally:lock.close()
