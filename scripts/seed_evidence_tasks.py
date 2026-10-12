"""Populate research plans, not invented findings, for the immersiveness pilot."""
from pathlib import Path
from construct_lab.etymology import EtymologyStore
from construct_lab.backup import create_backup
path=Path(__file__).resolve().parents[1]/'data/construct-lab.sqlite'
s=EtymologyStore(path);p=s.db.execute("SELECT project FROM etymology_pilots WHERE name='immersiveness'").fetchone()[0]
create_backup(path)
before={r[0]:s.export(r[0]) for r in s.db.execute('SELECT id FROM projects') if r[0]!=p}
records=s.etymology(p)['records']
for a in records:
 if a['kind']!='assessment':continue
 if any(r['kind']=='task' and any(l['id']==a['id'] for l in r['links']) for r in s.etymology(p)['records']):continue
 if a['stale']:continue
 linked=[next(r for r in records if r['id']==l['id']) for l in a['links']];d=next(r for r in linked if r['kind']=='definition')
 if 'Candidate A' in d['content']['title']:
  plan='Search scholarly indexes (e.g., Crossref, OpenAlex, university library) for "immersion sensory enclosure", "display coherence immersion" and "non immersive display absorption". Inspect original studies for independently varied enclosure and coordinated cues. Record citation, page/section, task setting and limitations; do not infer empirical support from dictionary meaning.'
 elif 'Candidate B' in d['content']['title']:
  plan='Search scholarly indexes and the university library for "immersion sustained attention absorption", "narrative engagement attention" and "task concentration presence". Prioritize studies distinguishing attention duration from immersion or absorption with separate measures. Record original results and competing explanations; do not treat the hypothetical case as an observation.'
 else:
  plan='Search scholarly indexes and the university library for "presence immersion interruptions", "experiential frame absorption" and "immersion context dependence". Seek studies distinguishing environmental capacity from reported state and transportation. Record operational definitions and counterevidence. If published evidence is inadequate, specify a new study rather than asserting resolution.'
 s.save_etymology(p,dict(kind='task',expected_version=0,actor='Assistant — research-plan preparation',reason='Seed an open evidence task from a provisional boundary judgment; no searches or findings asserted.',links=[dict(id=a['id'],version=a['version']),*a['links']],content=dict(title='Investigate: '+a['content']['title'],question=a['content']['evidence_needed'],search_plan=plan,owner='Unassigned',priority='high' if a['content']['classification']=='uncertain' else 'normal',status='open',findings_summary='No evidence reviewed for this task yet.',decision='pending',resolution='No decision yet. Compare evidence with the linked candidate definition before recommending retention or revision.')))
assert all(s.export(x)==v for x,v in before.items())
print('Pilot evidence tasks:',sum(r['kind']=='task' for r in s.etymology(p)['records']));print('Other projects unchanged');s.close()
