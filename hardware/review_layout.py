"""Annotated review drawing of the generated board; not manufacturing silkscreen."""
import json,re,sys
from pathlib import Path
from export_fab import svg,ROOT

a=json.loads((ROOT/'hardware/preamp_layout.json').read_text())
svg('preamp',a)
s=(ROOT/'docs/preamp_layout.svg').read_text()
s=re.sub(r'<svg[^>]*>', '<svg xmlns="http://www.w3.org/2000/svg" width="1900" height="1100" viewBox="-42 -9 185 113">',s,count=1)
s=s.replace('</svg>','')
s+='<text x="48" y="-4" text-anchor="middle" font-family="sans-serif" font-size="3.4" fill="#182c25">Rev B · dual-polarization antenna preamp · 96 × 96 mm</text>'
parts={p['ref']:p for p in a['parts']}
def label(ref,x,y,t1,t2):
 global s
 p=parts[ref];right=x>96;end=x-1 if right else x+35
 s+=f'<path d="M {p["x"]} {p["y"]} L {end} {y-1}" fill="none" stroke="#637b83" stroke-width=".25"/><circle cx="{p["x"]}" cy="{p["y"]}" r=".6" fill="#126b7e"/>'
 for dy,txt in [(0,t1),(2.7,t2)]:s+=f'<text x="{x}" y="{y+dy}" font-family="sans-serif" font-size="2.05" fill="#182c25" font-weight="{600 if dy==0 else 400}">{txt}</text>'
label('L103',-40,11,'L102 / L103 · X filter','100 / 120 nH · perpendicular')
label('T101',-40,30,'T101 · X input transformer','Mini-Circuits ADT1-1+')
label('T201',-40,49,'T201 · Y input transformer','Mini-Circuits ADT1-1+')
label('L203',-40,69,'L202 / L203 · Y filter','100 / 120 nH · perpendicular')
label('U101',100,9,'U101 · X RF amplifier','Mini-Circuits GALI-74+')
label('R108',100,28,'R108 / L105 · X bias','41.2 Ω / 1 µH')
label('U102',100,45,'U102 · X 8 V LDO','TI TPS7A4901')
label('U201',100,62,'U201 · Y RF amplifier','Mini-Circuits GALI-74+')
label('R208',100,77,'R208 / L205 · Y bias','41.2 Ω / 1 µH')
label('U202',100,92,'U202 · Y 8 V LDO','TI TPS7A4901')
s+='<text x="48" y="101" text-anchor="middle" font-family="sans-serif" font-size="2.1" fill="#182c25">Red: top copper · Blue: bottom copper · Ground planes hidden for clarity</text></svg>'
(ROOT/'docs/preamp_rev_b_annotated.svg').write_text(s)
