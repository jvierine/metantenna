"""Readable review diagram; proposed filter is not a released PCB circuit."""
from pathlib import Path
from xml.sax.saxutils import escape
R=Path(__file__).resolve().parent
items=[]
def line(x,y,u,v,color='#234b60',width=3):items.append(f'<path d="M{x},{y} L{u},{v}" stroke="{color}" stroke-width="{width}" fill="none"/>')
def text(x,y,s,size=19,anchor='middle',color='#203a46'):
 items.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" fill="{color}">{escape(s)}</text>')
def box(x,y,w,h,labels,fill='#eef5f7'):
 items.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="#688592" stroke-width="2"/>')
 for i,t in enumerate(labels):text(x+w/2,y+h/2+(i-(len(labels)-1)/2)*25+6,t)
def dot(x,y):items.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#234b60"/>')
text(600,38,'Bias tee — proposed power-input RFI filtering',27)
text(600,70,'For schematic review · common-mode filter not yet fitted to the PCB',18,color='#8b512b')
text(92,146,'12 V supply',20)
text(92,191,'+',20);text(92,271,'Return',18)
# Both supply conductors traverse the same common-mode choke before ground joins RF.
line(120,185,230,185);line(120,265,230,265)
box(230,140,240,170,['Coupled choke','Both +12 V and return','Component TBD'])
line(470,185,530,185);line(470,265,1010,265)
box(530,135,230,100,['Protection + differential','supply filtering'])
line(760,185,860,185)
box(800,330,120,80,['Bias choke','L10'])
line(860,185,860,330);line(860,410,860,465);line(860,465,510,465);line(510,465,510,510);dot(510,510)
line(1010,265,1010,345);text(1010,375,'RF ground',18);text(1010,401,'Coax shields',18)
text(260,348,'Keep input return isolated',18)
text(260,375,'from RF ground until after the choke.',18)
# RF ports: X injects DC on antenna side of blocking capacitor.
text(140,485,'X antenna + DC',20);text(1050,485,'X receiver',20)
line(140,510,677,510);line(677,494,677,526);line(691,494,691,526);line(691,510,1060,510)
text(684,555,'C10 · DC block',18)
text(140,615,'Y antenna',20);text(1050,615,'Y receiver',20)
line(140,640,677,640);line(677,624,677,656);line(691,624,691,656);line(691,640,1060,640)
text(684,685,'C20 · DC block',18)
text(600,745,'RF return paths remain continuous. No series choke in the shared RF ground plane.',18)
text(600,777,'Choke impedance, differential filter values and 30–55 MHz suppression require validation.',18)
(R/'biastee_filter_review.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="810" viewBox="0 0 1200 810"><rect width="1200" height="810" fill="white"/><g font-family="Arial, sans-serif">'+''.join(items)+'</g></svg>\n')
