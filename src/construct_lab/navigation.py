"""Shared project navigation and explicit next actions."""
from .demonstration import DemonstrationStore
class AppStore(DemonstrationStore):
 def navigation(self):
  demos={r[0] for r in self.db.execute('SELECT project FROM demonstrations')};items=[]
  for p in self.state()['projects']:
   pid=p['id'];w=self.workspace(pid);papers=self.papers(pid);accepted=[x for x in w['passages'] if x['status']=='verified'];pending=[x for x in w['passages'] if x['status']=='proposed']
   if pid in demos:action=dict(path='demonstration',label='Open guided demonstration',detail='All examples are populated. No forms or approvals are required. Use Next step to explore the eight-step tour.')
   elif not papers:action=dict(path='library',label='Import your first paper',detail='Open the library and choose a PDF to begin collecting evidence.')
   elif pending:action=dict(path='review',label='Review proposed passages',detail=f'{len(pending)} proposed passages await review. For research use, inspect the original PDF before accepting. This is not required to continue software development.')
   elif not accepted:action=dict(path='extract',label='Extract evidence',detail='Choose an imported paper and create evidence proposals. AI extraction requires a configured provider; manual passage selection is available in Review.')
   elif not w['project']['version']:action=dict(path='definitions',label='Prepare a definition',detail='Link accepted evidence and save a draft. Approve it only when the wording is ready for research use.')
   else:action=dict(path='dashboard',label='Open project overview',detail='Inspect coding, evidence gaps and stopping conditions. No data entry or approval is required to continue building the system.')
   items.append(dict(**p,demonstration=pid in demos,next=action))
  return dict(projects=items)
