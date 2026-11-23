"""Readable functional diagram of the implemented supply filter."""
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
text(600,38,'Bias tee — power-input RFI filtering',27)
text(600,70,'Implemented circuit · suppression requires bench verification',18,color='#8b512b')
text(92,146,'12 V supply',20)
text(92,191,'+',20);text(112,271,'Return',18,anchor='end')
# Both supply conductors traverse the same common-mode choke before ground joins RF.
line(120,185,230,185);line(120,265,230,265)
box(145,170,60,30,['F1'],'white')
box(230,140,240,170,['CM1 · TDK ACM7060','Both +12 V and return','700 Ω at 100 MHz'])
line(470,185,530,185);line(470,265,1010,265)
box(530,135,230,100,['D1 / D2 / C1','FB1 + C2/C3 + R1/C4'])
line(760,185,860,185)
box(800,330,120,80,['F10 + L10','DC injection'])
line(860,185,860,330);line(860,410,860,465);line(860,465,650,465);line(650,465,650,510);dot(650,510)
line(1010,265,1010,345);text(1010,375,'RF ground',18);text(1010,401,'Coax shields',18)
text(260,348,'Keep input return isolated',18)
text(260,375,'from RF ground until after the choke.',18)
# Each antenna-facing connector passes BOTH centre and shield through a CMC.
for y,ref,cap,label in [(510,'CM10','C10','X antenna + DC'),(730,'CM20','C20','Y antenna')]:
 text(140,y-25,label,20);text(1040,y-25,'X receiver' if ref=='CM10' else 'Y receiver',20)
 line(140,y,300,y);line(140,y+60,300,y+60)
 box(300,y-25,185,115,[ref,'Centre + shield'])
 line(485,y,795,y);line(795,y-16,795,y+16);line(809,y-16,809,y+16);line(809,y,1060,y)
 text(802,y+35,cap+' · DC block',17)
 if ref=='CM10':
  line(485,y+60,1060,y+60)
 else:
  line(485,y+60,795,y+60);line(795,y+44,795,y+76);line(809,y+44,809,y+76);line(809,y+60,1060,y+60)
  text(802,y+106,'C21 · prevents a parallel DC return',17)
 text(1040,y+90,'Indoor RF ground',17)
text(600,890,'Antenna-side shield islands stay separate from indoor ground except through the paired windings.',17)
text(600,920,'CM10 / CM20: TDK ACM4520-901-2P-T000 · JLC C41519 · factory-mounted SMD components',17)
(R/'biastee_filter_review.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="950" viewBox="0 0 1200 950"><rect width="1200" height="950" fill="white"/><g font-family="Arial, sans-serif">'+''.join(items)+'</g></svg>\n')
