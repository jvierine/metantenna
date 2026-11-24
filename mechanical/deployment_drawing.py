"""Dimensioned deployment drawing from the selected NEC geometry.

Engineering dimensions are in model metadata. Source/build provenance belongs
here and in data metadata, never in the visible drawing.
"""
from pathlib import Path
import json,math,html
R=Path(__file__).resolve().parents[1]
g=json.loads((R/'simulation/antenna/summary.json').read_text())['SIMONe_candidate']['geometry']
L=g['arm_length_m'];H=g['feed_height_m'];a=math.radians(g['slope_down_deg']);reach=.043+L*math.cos(a);tip=H-L*math.sin(a)
s=['''<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="950" viewBox="0 0 1400 950">
<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto-start-reverse"><path d="M0,0 L8,4 L0,8" fill="none" stroke="#52636d"/></marker></defs>
<rect width="1400" height="950" fill="white"/>
<style>text{font-family:serif;fill:#20313d;font-size:23px}.small{font-size:19px}.heading{font-size:28px;font-weight:bold}.dim{stroke:#52636d;stroke-width:1.2;fill:none;marker-start:url(#arrow);marker-end:url(#arrow)}.ext{stroke:#99a5ac;stroke-width:1;fill:none}.rope{stroke:#879097;stroke-width:2;stroke-dasharray:7 6;fill:none}</style>
''']
def line(x1,y1,x2,y2,stroke='#20313d',width=2,extra=''):
 s.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{stroke}" stroke-width="{width}" {extra}/>')
def text(x,y,t,cls='',anchor='middle',extra=''):
 s.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" class="{cls}" {extra}>{html.escape(t)}</text>')
def dim(x1,y1,x2,y2,label,tx,ty):
 s.append(f'<path class="dim" d="M{x1},{y1} L{x2},{y2}"/>');text(tx,ty,label,'small')
text(700,38,'Crossed inverted-V receive antenna — 32.55 MHz candidate','heading')
text(420,95,'Elevation: one dipole plane','heading');text(1110,95,'Plan view','heading')
scale=165;cx=420;ground=530;top=ground-H*scale
line(35,ground,825,ground,'#637867',2);text(75,ground+29,'Ground','small')
# Plastic mast and antenna enclosure.
s.append(f'<rect x="{cx-4}" y="{top}" width="8" height="{H*scale}" fill="#d3d9dc" stroke="#677983"/>')
s.append(f'<rect x="{cx-12}" y="{top-10}" width="24" height="13" fill="#edf0f2" stroke="#20313d"/>')
for sign in [-1,1]:
 x0=cx+sign*.043*scale;x1=cx+sign*reach*scale;y1=ground-tip*scale
 line(x0,top,x1,y1,'#0072b2',4)
 line(x1,y1,cx+sign*(reach+.36)*scale,ground,extra='class="rope"')
 line(cx+sign*(reach+.36)*scale-5,ground-4,cx+sign*(reach+.36)*scale+5,ground+9,'#637867',3)
 s.append(f'<circle cx="{x1}" cy="{y1}" r="4" fill="white" stroke="#0072b2" stroke-width="2"/>')
 # Wire-length dimension offset above the wire.
 off=25;dx=sign*math.sin(a)*off;dy=-math.cos(a)*off
 dim(x0+dx,top+dy,x1+dx,y1+dy,'',0,0)
 if sign==1:text((x0+x1)/2+dx,(top+y1)/2+dy-12,f'{L:.2f} m copper arm','small',extra=f'transform="rotate({g["slope_down_deg"]:.0f},{(x0+x1)/2+dx},{(top+y1)/2+dy-12})"')
text(235,405,'Nylon support rope','small');line(240,416,105,485,'#879097',1)
# Dimensions.
dim(65,top,65,ground,'',0,0)
line(65,top,cx-15,top,'#99a5ac',1)
dim(790,ground-tip*scale,790,ground,f'{tip:.2f} m',750,ground-tip*scale/2)
line(cx+reach*scale,ground-tip*scale,800,ground-tip*scale,'#99a5ac',1)
dim(cx-reach*scale,580,cx+reach*scale,580,f'{2*reach:.2f} m tip-to-tip',cx,570)
for sign in [-1,1]:line(cx+sign*reach*scale,ground-tip*scale,cx+sign*reach*scale,587,'#99a5ac',1)
text(45,(top+ground)/2,f'{H:.2f} m','small',extra=f'transform="rotate(-90,45,{(top+ground)/2})"');text(cx+90,top+22,f'{g["slope_down_deg"]:.0f}°','small');line(cx,top,cx+150,top,'#99a5ac',1,extra='stroke-dasharray="4 4"')
text(cx+70,450,'Ø50 mm plastic mast','small',anchor='start');line(cx+62,440,cx+5,437,'#879097',1)
for offset,color in [(-9,'#0072b2'),(9,'#d55e00')]:line(cx+offset,top+4,cx+offset,ground-15,color,1.6)
# Plan: two orthogonal planes, colours distinguish X/Y.
px=1110;py=325;ps=90
for dx,dy,label,col in [(-1,0,'X−','#0072b2'),(1,0,'X+','#0072b2'),(0,-1,'Y−','#d55e00'),(0,1,'Y+','#d55e00')]:
 line(px+dx*.043*ps,py+dy*.043*ps,px+dx*reach*ps,py+dy*reach*ps,col,4)
 text(px+dx*(reach*ps+27),py+dy*(reach*ps+27)+7,label)
s.append(f'<rect x="{px-6}" y="{py-6}" width="12" height="12" fill="#edf0f2" stroke="#20313d"/>')
text(px,568,'Four equal arms; 90° between dipole planes','small')
# Wiring detail.
text(700,650,'Connections','heading')
s.append('<rect x="80" y="705" width="250" height="125" rx="6" fill="#f3f6f5" stroke="#20313d"/>')
text(205,740,'Antenna head');text(205,775,'X / Y preamps','small');text(205,805,'Both powered from X','small')
s.append('<rect x="720" y="685" width="240" height="100" rx="6" fill="#f3f6f5" stroke="#20313d"/>')
text(840,725,'X bias tee');text(840,757,'12 V DC input','small')
s.append('<rect x="1110" y="705" width="210" height="125" rx="6" fill="#f3f6f5" stroke="#20313d"/>')
text(1215,745,'Two-channel');text(1215,777,'50 Ω receiver')
line(330,730,720,730,'#0072b2',3);line(960,730,1110,730,'#0072b2',3)
text(525,714,'X: RF + 12 V DC','small')
line(330,805,1110,805,'#d55e00',3);text(680,834,'Y: RF only, DC blocked at antenna head','small')
text(700,884,'Four copper wires solder to the PCB; two SMA outputs. Coax runs up to 50 m.','small')
text(700,918,'2 mm bare copper assumed. Tip heights exclude support-rope sag.','small')
s.append('</svg>')
# Empty dimension labels are omitted rather than rendered.
s=[v for v in s if not ('<text x="0"' in v)]
(R/'vhf/docs/antenna_deployment.svg').write_text('\n'.join(s))
