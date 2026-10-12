"""Seed nine provisional development judgments, never overwriting existing pairs."""
from pathlib import Path
from construct_lab.etymology import EtymologyStore
from construct_lab.backup import create_backup
path=Path(__file__).resolve().parents[1]/'data/construct-lab.sqlite'
s=EtymologyStore(path);p=s.db.execute("SELECT project FROM etymology_pilots WHERE name='immersiveness'").fetchone()[0]
create_backup(path)
before={r[0]:s.export(r[0]) for r in s.db.execute('SELECT id FROM projects') if r[0]!=p}
records=s.etymology(p)['records'];definitions={r['content']['title'].split(' — ')[0]:r for r in records if r['kind']=='definition'};cases={r['content']['title']:r for r in records if r['kind']=='case'}
rows=[
('Absorbing book','Candidate A','excluded','A printed novel in an ordinary room does not supply coordinated surrounding sensory stimulation. Deep engagement alone is excluded by A.','Document the actual sensory arrangement; test whether readers still report immersion without enclosure.'),
('Absorbing book','Candidate B','included','Deep engagement is provisionally read as sustained attention. The scenario does not specify duration, so this judgment relies on that explicit assumption.','Observe attention over time and distinguish sustained engagement from momentary interest.'),
('Absorbing book','Candidate C','uncertain','Being absorbed does not by itself show that the narrative organizes perception and interpretation as a dominant experiential frame.','Collect descriptions of experiential framing and vary interruptions; separate framing capacity from its realized state.'),
('Interrupted simulation','Candidate A','uncertain','Rich surrounding visuals suggest enclosure, but the scenario does not establish coordinated sensory input, which A requires. Interruptions alone do not rule out A.','Audit coordination of sensory cues rather than inferring it from visual richness.'),
('Interrupted simulation','Candidate B','uncertain','Mandatory interruptions may break sustained attention, but their timing and the focal episode are unspecified.','Specify the observation window; measure attention before, during and after interruptions.'),
('Interrupted simulation','Candidate C','uncertain','Disruption may limit realized experiential dominance; it does not alone establish absence of capacity under the specified context.','Manipulate interruption demands and measure experiential framing separately from technological capacity.'),
('Focused spreadsheet','Candidate A','excluded','Ordinary spreadsheet concentration does not establish surrounding sensory enclosure.','Verify the presentation setting; compare ordinary and surrounding displays at matched task demands.'),
('Focused spreadsheet','Candidate B','included','Intense concentration provisionally meets B if sustained. Lack of transportation is not an exclusion in B.','Measure duration of focused attention and ask whether participants distinguish it from immersion.'),
('Focused spreadsheet','Candidate C','uncertain','Not feeling transported is not equivalent to lacking a dominant experiential frame. Candidate C needs a clearer operational boundary.','Ask whether the task organizes perception and interpretation; test framing separately from transportation and attention.')]
for case,key,label,reason,evidence in rows:
 c=cases[case];d=definitions[key];pair={c['id'],d['id']}
 if any(r['kind']=='assessment' and pair.issubset({x['id'] for x in r['links']}) for r in s.etymology(p)['records']):continue
 s.save_etymology(p,dict(kind='assessment',expected_version=0,actor='Assistant — provisional pilot coder',reason='Populate boundary-case demonstration; not researcher approval or independent validation.',links=[dict(id=r['id'],version=r['version']) for r in [c,d]],content=dict(title=case+' × '+key,classification=label,rationale=reason,evidence_needed=evidence,assessor_independence='Assistant-authored judgment with prior exposure to the definitions and development cases; not independent or blinded.',limitations='Hypothetical development case, not observed empirical evidence. Classification does not establish construct validity, causal support or saturation.')))
assert all(s.export(x)==v for x,v in before.items())
print('Nine pilot pairs ready; other projects unchanged.');s.close()
