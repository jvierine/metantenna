"""Insert the two GALI input DC blocks without rerouting unrelated copper.
Retains cached RevB routes; reroutes only the input/filter and input-pin nets.
"""
from pathlib import Path
import json
from shapely.geometry import LineString,Point
import build as b
from design import preamp
r=b.ROOT;path=r/'hardware/preamp_layout.json';d=json.loads(path.read_text());parts,size=preamp();router=b.Router(parts,size)
changed={'X_AMP_IN','Y_AMP_IN','X_GALI_IN','Y_GALI_IN'}
router.tracks=[t for t in d['tracks'] if t[0] not in changed];router.vias=[t for t in d['vias'] if t[0] not in changed]
for n,l,a,z,w in router.tracks:router.obstacles.append((n,LineString([a,z]).buffer(w/2),[l]))
for n,x,y in router.vias:router.obstacles.append((n,Point(x,y).buffer(.3),[0,1]))
for net in sorted(changed):
 pads=[p for p in router.pads if p['net']==net]
 for q in pads[1:]:router.connect(net,(pads[0]['x'],pads[0]['y']),(q['x'],q['y']),True)
b.pcb('preamp',parts,size,router)
print('Preserved unrelated routes; updated',sorted(changed))
