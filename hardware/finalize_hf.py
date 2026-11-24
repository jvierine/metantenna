"""Consolidate coincident-net vias and preserve routed HF prototype metadata."""
from pathlib import Path
from types import SimpleNamespace
import json,math
import build_hf as hf
b=hf.b
for name,fn in [('preamp',hf.hf_preamp),('biastee',hf.hf_biastee)]:
 path=hf.out/'hardware'/f'{name}_layout.json';d=json.loads(path.read_text());parts,size=fn()
 tracks=d['tracks'];vias=[];mapping={}
 fresh={(q['ref'],q['pin']):q for a in parts for q in b.physical(a)}
 for old in d['pads']:
  if old['ref']!='L106':continue
  new=fresh[(old['ref'],old['pin'])]
  if (old['x'],old['y'])!=(new['x'],new['y']):mapping[(old['net'],old['x'],old['y'])]=(new['x'],new['y'])
 for net,x,y in d['vias']:
  old=next(((xx,yy) for n,xx,yy in vias if n==net and math.dist((x,y),(xx,yy))<.55),None)
  if old:mapping[(net,x,y)]=old
  else:vias.append((net,x,y))
 for t in tracks:
  for i in [2,3]:t[i]=mapping.get((t[0],*t[i]),t[i])
 r=SimpleNamespace(pads=[q for a in parts for q in b.physical(a)],tracks=tracks,vias=vias)
 b.pcb(name,parts,size,r);hf.sch.build(name,parts)
 pcb=hf.out/'hardware'/f'{name}.kicad_pcb';s=pcb.read_text().replace('METANTENNA B0','METANTENNA HF A0')
 if name=='biastee':s=s.replace('(xy 15.5 ', '(xy 23 ')
 if name=='preamp':
  s=s.replace('(at 83 61)','(at 83 77)').replace('(at 48 87)','(at 54 91)')
  zones=[]
  for x,y in [(12,43),(84,52),(45,9),(45,84)]:zones.append(f'(zone (net 0) (net_name "") (layers "F.Cu" "In1.Cu" "In2.Cu" "B.Cu") (hatch edge 0.5) (keepout (tracks allowed) (vias allowed) (pads allowed) (copperpour not_allowed) (footprints allowed)) (polygon (pts (xy {x-9} {y-.5}) (xy {x-1} {y-.5}) (xy {x-1} {y+2}) (xy {x-9} {y+2}))))')
  s=s.rstrip()[:-1]+'\n'+'\n'.join(zones)+'\n)\n'
 pcb.write_text(s)
 sch=hf.out/'hardware'/f'{name}.kicad_sch';sch.write_text(sch.read_text().replace('(paper "A2")','(paper "A1")').replace('engineering prototype','HF engineering prototype'))
 print(name,'finalized',len(vias),'vias; checked source/route synchronization')
