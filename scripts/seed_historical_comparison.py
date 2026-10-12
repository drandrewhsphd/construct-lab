"""Add a bounded, sourced historical comparison without overwriting researcher edits."""
from pathlib import Path
from construct_lab.etymology import EtymologyStore,SCHEMA
from construct_lab.backup import create_backup
s=EtymologyStore(Path(__file__).resolve().parents[1]/'data/construct-lab.sqlite')
p=s.db.execute("SELECT project FROM etymology_pilots WHERE name='immersiveness'").fetchone()[0]
create_backup(Path(__file__).resolve().parents[1]/'data/construct-lab.sqlite')
before={r[0]:s.export(r[0]) for r in s.db.execute('SELECT id FROM projects') if r[0]!=p}
def add(kind,values,links=()):
 for r in s.etymology(p)['records']:
  if r['kind']==kind and r['content']['title']==values[0]:return r
 return s.save_etymology(p,dict(kind=kind,content=dict(zip(SCHEMA[kind],values,strict=True)),links=list(links),expected_version=0,actor='Assistant — historical comparison pilot',reason='Add sourced historical anchor and provisional comparison; no researcher approval.'))['records'][-1]
def ref(r):return dict(id=r['id'],version=r['version'])
h=add('historical',['Slater & Wilbur (1997) — technological immersion','immersion (related term, not an exact immersiveness definition)','1997','Slater, M., & Wilbur, S. (1997). A Framework for Immersive Virtual Environments (FIVE): Speculations on the Role of Presence in Virtual Environments. Presence, 6(6), 603–616. doi:10.1162/pres.1997.6.6.603','https://direct.mit.edu/pvar/article/6/6/603/18157/A-Framework-for-Immersive-Virtual-Environments','Paraphrase: immersion is assessable through technological characteristics, including how fully a display surrounds the participant and the breadth and vividness of its sensory presentation.','Technology / display system','Virtual environments; distinguishes technological immersion from the psychological state of presence.','Publisher abstract, accessed 2026-10-09; full article not inspected for this entry.','One historical scholarly account, not a comprehensive history or proof of first use. Immersion and immersiveness must not be treated as synonymous without argument.'])
records=s.etymology(p)['records'];sources=[ref(r) for r in records if r['kind']=='source'];defs=[r for r in records if r['kind']=='definition']
rows=[
['A — enclosure compared with 1997 immersion','The technological focus and surrounding sensory presentation. The physical linguistic sense supplies an analogy.','Narrows the broader historical account to coordinated sensory enclosure.','Other features discussed in the historical abstract, including body matching and an actionable plot, are not explicit in candidate A.','Defensible only if the intended construct is a narrower environmental property; label the narrower scope rather than claiming a wholly new theory.','Compare enclosing but inconsistent environments with non-enclosing coherent experiences; examine whether the proposed scope loses explanatory value.'],
['B — engagement compared with 1997 immersion','The figurative linguistic association with deep engagement.','Moves from technological characteristics to a participant psychological state. This is a level-of-analysis change, not a simple wording update.','Surrounding sensory technology is no longer required.','Requires a reason to distinguish this construct from sustained attention and absorption; historical terminology alone cannot justify that distinction.','Compare sustained spreadsheet attention with absorbing narrative experiences using independently developed measures.'],
['C — framing capacity compared with 1997 immersion','The environmental contribution while allowing the figurative engagement interpretation.','Moves from a technological property to a capacity contingent on participant and context.','Sensory richness alone is insufficient; contemporary presence measures cannot automatically serve as equivalent measures.','A relational definition may explain context dependence, but capacity and experienced state need separate measures.','Manipulate coherence and interruption demands independently, and test the proposed interaction rather than assuming it.']]
for d,v in zip(defs,rows,strict=True):
 add('comparison',v+['Assistant-authored provisional comparison, not a finding. One scholarly anchor and two dictionary entries are not an exhaustive historical search. Definitions differ in level of analysis.'],[ref(h),ref(d),*sources])
assert all(s.export(x)==v for x,v in before.items())
print('Historical definition and 3 comparisons ready; other projects unchanged.');s.close()
