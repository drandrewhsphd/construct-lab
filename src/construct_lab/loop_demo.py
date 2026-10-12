"""Deterministic synthetic plumbing fixture. Never an AI or empirical result."""
def demo_output(stage, inputs):
 evidence=inputs['evidence'][0]['id'];previous=inputs['previous_items']
 items=[]
 def add(ident,kind,title,content,refs):items.append(dict(id=ident,kind=kind,title=title,content=content,refs=refs))
 if stage=='generate':
  add('i1','interpretation','Synthetic interpretive bridge',dict(claim='Consider encompassing attention.',bridge='A semantic analogy suggests a candidate; it does not establish its validity.',assumptions='Transfer from linguistic usage to the target setting requires evidence.',alternative='A property of the environment rather than the person.'),[evidence])
  for n,unit in [('c1','Person in an episode'),('c2','Environment in an episode')]:
   add(n,'candidate','Synthetic candidate '+n,dict(definition='A provisional encompassing quality requiring a specified referent.',unit=unit,inclusion='Specified referent and episode.',exclusion='Mere liking without encompassing quality.',rival='Engagement or presence.'),['i1',evidence])
  for n,role in [('r1','antecedent'),('r2','outcome')]:
   add(n,'relationship','Synthetic '+role,dict(role=role,mechanism='Hypothesized attentional allocation.',prediction='A discriminating change under controlled conditions.',rival='Task interest explains the association.',test='Measure interest separately and compare competing predictions.'),['c1',evidence])
 else:
  candidate=[x['id'] for x in previous if x['kind'] in ('candidate','revision')][-1]
  if stage=='challenge':
   for n in ('1','2'):
    add('case'+n,'case','Synthetic contrast '+n,dict(scenario='Constructed episode with attention but uncertain encompassing quality.',purpose='Distinguish attention from the proposed property.'),[candidate])
    add('a'+n,'assessment','Synthetic uncertain judgment '+n,dict(classification='uncertain',rationale='The vignette omits discriminating information.',evidence_needed='Observe the referent and distinguish task interest.'),['case'+n,candidate])
   add('challenge1','challenge','Synthetic rival challenge',dict(critique='Definition may overlap with engagement.',rival='Engagement alone explains the episode.',test='Find episodes that separate engagement and encompassing quality.'),[candidate])
  elif stage=='plan':
   challenge=next(x['id'] for x in previous if x['kind']=='challenge')
   for n in ('1','2'):
    add('task'+n,'task','Synthetic evidence task '+n,dict(question='What evidence distinguishes this candidate from engagement?',search_plan='Inspect historical usage and neighboring-construct definitions; seek disconfirming examples.',priority='high',decision_rule='Revise if the distinction collapses; retain provisionally if independently supported.'),[challenge])
  else:
   new=inputs['new_evidence_ids'][0]
   add('v1','revision','Synthetic revised candidate',dict(before_id=candidate,definition='A provisional encompassing quality with an explicit episode and referent.',unit='Specified referent in an episode.',inclusion='Documented encompassing quality.',exclusion='Attention or interest alone.',rationale='Synthetic demonstration of linking new evidence to a revision; not a substantive inference.',limitations='Requires real source review and empirical evaluation.'),[candidate,new])
   add('r1','relationship','Synthetic updated outcome',dict(role='outcome',mechanism='Hypothesized allocation of attention.',prediction='Distinct from task interest.',rival='Engagement explains the result.',test='Compare rival predictions with independent measures.'),['v1',new])
 return dict(summary='SYNTHETIC DEMONSTRATION: workflow mechanics only; no AI call.',limitations='These canned examples do not analyze your sources or validate a construct.',items=items)
