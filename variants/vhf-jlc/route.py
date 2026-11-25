"""Local routing repair for larger manufacturer-recommended APV solder lands."""
from pathlib import Path
import sys,json
import sexpdata as sx
from sexpdata import Symbol as S
from shapely.geometry import LineString,Point
R=Path(__file__).resolve().parents[2];O=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'hardware'))
import build as b
from design import Part
old=b.pads
def pads(pkg):
 if pkg in ['APV2012','APV2520']:
  pitch,h=(.89,1.78) if pkg=='APV2012' else (1.145,2.54)
  return [('1',-pitch,0,1.02,h,0),('2',pitch,0,1.02,h,0)]
 return old(pkg)
b.pads=pads
name='preamp';path=O/'hardware/preamp_layout.json';d=json.loads(path.read_text());parts=[Part(**p) for p in d['parts']];rr=b.Router(parts,d['size_mm']);changed={'X_RAW','X_COAX','X_LP1','X_LP2','Y_LP1','Y_LP2'}
rr.tracks=[t for t in d['tracks'] if t[0] not in changed];rr.vias=[v for v in d['vias'] if v[0] not in changed]
for n,l,a,z,w in rr.tracks:rr.obstacles.append((n,LineString([a,z]).buffer(w/2),[l]))
for n,x,y in rr.vias:rr.obstacles.append((n,Point(x,y).buffer(.3),[0,1]))
for net in sorted(changed):
 pp=[p for p in rr.pads if p['net']==net]
 for p in pp[1:]:rr.connect(net,(pp[0]['x'],pp[0]['y']),(p['x'],p['y']),True)
d['tracks']=rr.tracks;d['vias']=rr.vias;path.write_text(json.dumps(d,indent=2)+'\n')
def tag(x,k):return isinstance(x,list) and x and str(x[0])==k
p=O/'hardware/preamp.kicad_pcb';tree=sx.load(open(p));nets={str(x[2]):int(x[1]) for x in tree if tag(x,'net')};tree[:]=[x for x in tree if not tag(x,'segment') and not tag(x,'via')]
for n,l,a,z,w in rr.tracks:tree.append(sx.loads(f'(segment (start {a[0]:.4f} {a[1]:.4f}) (end {z[0]:.4f} {z[1]:.4f}) (width {w}) (layer "{["F.Cu","B.Cu"][l]}") (net {nets[n]}))'))
for n,x,y in rr.vias:tree.append(sx.loads(f'(via (at {x:.4f} {y:.4f}) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net {nets[n]}))'))
p.write_text('('+str(tree[0])+'\n'+'\n'.join(sx.dumps(q) for q in tree[1:])+'\n)\n');print('Rerouted only',sorted(changed))
