from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
import textwrap
out=Path('data/demonstration')
examples=[('Starting concept','In this invented example, a learner asks how an unfamiliar tool works because they want to understand its mechanism. This illustrates a learning motive, not a finding about actual participants.'),('Boundary challenge','In this invented example, a learner requests information both to understand a tool and to feel reassured about making a mistake. The two motives coexist; a request alone does not identify either motive.'),('Confirming example','In this invented example, another learner asks for an explanation of the same tool to improve understanding. Within this scripted scenario, it confirms the learning-oriented example without introducing an additional concept.')]
for i,(title,body) in enumerate(examples,1):
 c=canvas.Canvas(str(out/f'demo-evidence-{i}.pdf'),pagesize=(612,792));c.setTitle('SYNTHETIC DEMONSTRATION - '+title);c.setAuthor('Construct Lab system demonstration')
 c.setFillColor(HexColor('#203748'));c.setFont('Helvetica-Bold',12);c.drawString(48,736,'CONSTRUCT LAB / SYNTHETIC DEMONSTRATION')
 c.setFont('Helvetica-Bold',23);c.drawString(48,686,title)
 c.setFont('Helvetica',12);y=635
 for line in textwrap.wrap(body,78):c.drawString(48,y,line);y-=20
 c.setFont('Helvetica-Bold',12);c.drawString(48,y-35,'Invented training material. Not a published study.')
 c.setFont('Helvetica',11);c.drawString(48,68,f'Demonstration evidence {i} of 3 | Page 1');c.save()
