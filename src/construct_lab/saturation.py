"""Project stopping criteria: decision support, never automatic proof of saturation."""
import json
from uuid import uuid4
from .novelty import NoveltyStore
from .store import Conflict, required

DEFAULTS=dict(rounds=3,min_passages=5,max_novelty_percent=5)
GATES=('literature_coverage','coding_validation','contradictions_and_boundaries')
class SaturationStore(NoveltyStore):
 def __init__(self,path):
  super().__init__(path)
  self.db.execute('''CREATE TABLE IF NOT EXISTS saturation_rules(project TEXT NOT NULL,version INTEGER NOT NULL,payload TEXT NOT NULL,actor TEXT NOT NULL,reason TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(project,version))''')
 def context(self,project):
  n=self.novelty(project);r=self.rounds(project)
  return self.digest(dict(snapshot=self.snapshot(project),rounds=[x['id'] for x in r['rounds']],assessments=[dict(id=x['id'],version=x['version'],content=x['content']) for x in n['records']]))
 def saturation(self,project):
  n=self.novelty(project);r=self.rounds(project);digest=self.context(project)
  history=[dict(x,payload=json.loads(x['payload'])) for x in self.db.execute('SELECT * FROM saturation_rules WHERE project=? ORDER BY version DESC',(project,))]
  latest=history[0] if history else None;payload=latest['payload'] if latest else dict(rules=DEFAULTS,checks={k:dict(status='unknown',rationale='') for k in GATES},context=None)
  rules=payload['rules'];conditions=[]
  def add(name,state,detail):conditions.append(dict(name=name,status=state,detail=detail))
  add('Rules configured','met' if latest else 'unknown','Saved project-specific criteria.' if latest else 'Illustrative defaults only; save a reasoned configuration before use.')
  add('Approved definition','met' if n['project']['version'] else 'unmet','Current approved version: '+str(n['project']['version']))
  post=[s for s in n['summary'] if not s['baseline']];window=post[-rules['rounds']:];enough=len(window)==rules['rounds']
  add('Consecutive evidence rounds','met' if enough else 'unmet',f"{len(window)} of {rules['rounds']} required post-baseline rounds. Empty or incomplete rounds are not skipped.")
  complete=enough and all(s['eligible']>=rules['min_passages'] and s['research_reviewed']==s['eligible'] and s['unresolved']==0 for s in window)
  add('Round assessment completeness','met' if complete else 'unmet',f"Each round needs at least {rules['min_passages']} eligible passages, all reviewed in research mode, with no unresolved judgments. Demonstrations and drafts do not qualify.")
  low=complete and all(100*s['novel']/s['decided']<=rules['max_novelty_percent'] for s in window)
  add('Low theoretical novelty','met' if low else 'unmet' if complete else 'unknown',f"Every round must be at or below {rules['max_novelty_percent']}% novel/challenging judgments among decided research assessments. Incomplete review cannot imply low novelty.")
  rounds=r['rounds'][-rules['rounds']:];stable=enough and all(not x['delta']['definition_changed'] for x in rounds)
  add('Definition stability','met' if stable else 'unmet' if enough else 'unknown','No approved-definition changes across the required post-baseline rounds.')
  unresolved=[q for q in self.learning(project)['questions'] if q['status']!='resolved']
  add('Research questions resolved','met' if not unresolved else 'unmet',f'{len(unresolved)} open, investigating or deferred questions remain.')
  preview=r['preview'];pending=preview is None or preview['definition_changed'] or any(preview[k][a] for k in ('papers','passages','coding','questions') for a in ('added','changed','removed'))
  add('Current evidence checkpointed','unmet' if pending else 'met','Record a new evidence round after changes.' if pending else 'Current evidence matches the latest saved round.')
  current=payload['context']==digest
  for k in GATES:
   c=payload['checks'][k];add(k.replace('_',' ').capitalize(),c['status'] if current else 'unknown',c['rationale'] if current and c['rationale'] else 'Needs a documented assessment of current evidence.' if not latest else 'Evidence changed since this check. Reassess before relying on it.')
  eligible=all(c['status']=='met' for c in conditions)
  return dict(project=n['project'],version=latest['version'] if latest else 0,rules=rules,checks=payload['checks'],checks_current=current,context=digest,conditions=conditions,history=history,window=window,recommendation='Consider a documented stopping decision' if eligible else 'Continue evidence development',explanation='All configured conditions are met; this supports researcher consideration, not proof of universal saturation.' if eligible else 'One or more conditions are unmet or unknown. No saturation or stopping claim is supported by this rule evaluation.')
 def save_saturation(self,project,b):
  actor=required(b.get('actor'));reason=required(b.get('reason'));rules=b.get('rules');checks=b.get('checks')
  if not isinstance(rules,dict) or set(rules)!=set(DEFAULTS) or any(type(v) is not int for v in rules.values()):raise ValueError('Use whole numbers for all thresholds')
  if not 1<=rules['rounds']<=20 or not 1<=rules['min_passages']<=10000 or not 0<=rules['max_novelty_percent']<=100:raise ValueError('Threshold outside allowed range')
  if not isinstance(checks,dict) or set(checks)!=set(GATES):raise ValueError('Complete the three evidence checks')
  for c in checks.values():
   if not isinstance(c,dict) or set(c)!={'status','rationale'} or c['status'] not in ('unknown','met','unmet') or not isinstance(c['rationale'],str) or len(c['rationale'])>10000:raise ValueError('Invalid evidence check')
   if c['status']!='unknown':required(c['rationale'])
  if len(actor)>200 or len(reason)>10000:raise ValueError('Name or rationale is too long')
  with self.db:
   self.db.execute('BEGIN IMMEDIATE');state=self.saturation(project)
   if b.get('expected_version')!=state['version'] or b.get('context')!=state['context']:raise Conflict('Rules or evidence changed. Reload and reconsider your checks before saving.')
   payload=dict(rules=rules,checks=checks,context=state['context'])
   self.db.execute('INSERT INTO saturation_rules(project,version,payload,actor,reason) VALUES(?,?,?,?,?)',(project,state['version']+1,json.dumps(payload),actor,reason))
  return self.saturation(project)
 def dashboard(self,project):
  d=super().dashboard(project);s=self.saturation(project);d['stopping_rules']=dict(recommendation=s['recommendation'],conditions=s['conditions']);return d
 def export(self,project):
  d=super().export(project);d['saturation_rules']=self.saturation(project);return d
