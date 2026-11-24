"""Build isolated HF prototype CAD using shared four-layer tooling.
Run base conda; never overwrites VHF or pfeffer-review sources.
"""
from pathlib import Path
import json
import build as b
import schematic as sch
from hf_design import hf_preamp,hf_biastee
R=Path(__file__).resolve().parents[1];out=R/'hardware/hf';out.mkdir(exist_ok=True);(out/'hardware').mkdir(exist_ok=True);(out/'manufacturing').mkdir(exist_ok=True)
old=b.pads
def pads(pkg):
 if pkg=='SOT23':return [('1',-.95,-.95,1,.6,0),('2',-.95,.95,1,.6,0),('3',.95,0,1,.6,0)]
 if pkg=='SRN6045':return [('1',-2.5,0,2.4,5.5,0),('2',2.5,0,2.4,5.5,0)]
 if pkg=='SOIC8':return [(str(i+1),-2.7,-1.905+i*1.27,1.55,.6,0) for i in range(4)]+[(str(i+5),2.7,1.905-i*1.27,1.55,.6,0) for i in range(4)]
 if pkg=='SRF0905':return [('1',-3.75,-1.27,2,1.2,0),('2',-3.75,1.27,2,1.2,0),('3',3.75,1.27,2,1.2,0),('4',3.75,-1.27,2,1.2,0)]
 if pkg=='IND5':return [('1',-2.1,0,1.8,4.4,0),('2',2.1,0,1.8,4.4,0)]
 return old(pkg)
b.pads=pads;b.ROOT=out;sch.ROOT=out
oldpins=sch.pins
def pins(p):
 if p.package=='SOT23':return [('1',0,7.62,270),('2',0,-7.62,90),('3',-7.62,0,0)]
 if p.package=='SOIC8':return [(str(i+1),-7.62,3.81-2.54*i,0) for i in range(4)]+[(str(i+5),7.62,-3.81+2.54*i,180) for i in range(4)]
 if p.package=='SRF0905':return [('1',-7.62,2.54,0),('2',-7.62,-2.54,0),('3',7.62,-2.54,180),('4',7.62,2.54,180)]
 return oldpins(p)
sch.pins=pins
class HFRouter(b.Router):
 def connect(self,net,p,q,rf):
  import math,heapq,numpy as np,shapely
  from shapely.geometry import Point,LineString
  step=b.STEP;width=b.WIDTH if rf else .2
  blocked=self.raster(net,width)
  # Vectorized conservative via mask replaces per-node Shapely calls.
  # This keeps two-layer escape searches bounded without relaxing clearance.
  via_blocked=self.raster(net,.6).any(axis=0)
  for pad in self.pads:
   g=pad['shape'].buffer(.4);x0,y0,x1,y1=g.bounds
   i0=max(0,int(x0/step));i1=min(self.nx-1,math.ceil(x1/step));j0=max(0,int(y0/step));j1=min(self.ny-1,math.ceil(y1/step))
   if i1<i0 or j1<j0:continue
   xx,yy=np.meshgrid(np.arange(i0,i1+1)*step,np.arange(j0,j1+1)*step,indexing='ij')
   via_blocked[i0:i1+1,j0:j1+1]|=shapely.contains_xy(g,xx,yy)
  start=(0,round(p[0]/step),round(p[1]/step));end=(0,round(q[0]/step),round(q[1]/step))
  if blocked[start] or blocked[end]:raise RuntimeError(('blocked pad',net,p,q))
  def search(layers):
   def heur(t):return max(abs(t[1]-end[1]),abs(t[2]-end[2]))+.4143*min(abs(t[1]-end[1]),abs(t[2]-end[2]))+20*t[0]
   heap=[(heur(start),0,start)];dist={start:0};prev={}
   while heap:
    _,d,u=heapq.heappop(heap)
    if d!=dist[u]:continue
    if u==end:return prev
    layer,x,y=u
    cs=[((layer,x+dx,y+dy),1 if dx==0 or dy==0 else 1.4143) for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]]
    if layers and not via_blocked[x,y]:cs.append(((1-layer,x,y),30))
    for v,cost in cs:
     ll,xx,yy=v
     if not(0<=xx<self.nx and 0<=yy<self.ny) or blocked[v]:continue
     nd=d+cost
     if nd<dist.get(v,float('inf')):dist[v]=nd;prev[v]=u;heapq.heappush(heap,(nd+heur(v),nd,v))
   return None
  prev=search(not rf)
  if prev is None and rf and '_ANT_' not in net:prev=search(True)
  if prev is None:raise RuntimeError(('unrouted',net,p,q))
  route=[end]
  while route[-1]!=start:route.append(prev[route[-1]])
  route.reverse();points=[(0,*p)]+[(l,x*step,y*step) for l,x,y in route]+[(0,*q)];compressed=[points[0]]
  for i in range(1,len(points)-1):
   a,c,e=compressed[-1],points[i],points[i+1]
   if a[0]==c[0]==e[0] and abs((c[1]-a[1])*(e[2]-c[2])-(c[2]-a[2])*(e[1]-c[1]))<1e-8:continue
   compressed.append(c)
  compressed.append(points[-1])
  for a,c in zip(compressed,compressed[1:]):
   if a[0]!=c[0]:self.vias.append((net,a[1],a[2]));self.obstacles.append((net,Point(a[1],a[2]).buffer(.3),[0,1]))
   elif math.dist(a[1:],c[1:])>1e-7:self.tracks.append((net,a[0],a[1:],c[1:],width));self.obstacles.append((net,LineString([a[1:],c[1:]]).buffer(width/2),[a[0]]))
 def antenna_feeds(self):return set()
 def power_spine(self):return set()
if __name__=='__main__':
 for name,fn in [('preamp',hf_preamp),('biastee',hf_biastee)]:
  parts,size=fn()
  # No package or body overlaps may be hidden by a schematic-only build.
  r=HFRouter(parts,size).run();b.pcb(name,parts,size,r);sch.build(name,parts)
  path_s=out/'hardware'/f'{name}.kicad_sch';path_s.write_text(path_s.read_text().replace('(paper "A2")','(paper "A1")').replace('engineering prototype','HF engineering prototype'))
  path=out/'hardware'/f'{name}.kicad_pcb';text=path.read_text().replace('METANTENNA B0','METANTENNA HF A0')
  if name=='biastee':text=text.replace('(xy 15.5 ', '(xy 23 ')
  # Keep high-Z arm input routes free of plane capacitance. Small local
  # windows on all layers; retain reference below low-impedance RF routes.
  if name=='preamp':
   zones=[]
   for x,y in [(12,43),(84,52),(45,9),(45,84)]:
    zones.append(f'(zone (net 0) (net_name "") (layers "F.Cu" "In1.Cu" "In2.Cu" "B.Cu") (hatch edge 0.5) (keepout (tracks allowed) (vias allowed) (pads allowed) (copperpour not_allowed) (footprints allowed)) (polygon (pts (xy {x-9} {y-.5}) (xy {x-1} {y-.5}) (xy {x-1} {y+2}) (xy {x-9} {y+2}))))')
   text=text.rstrip()[:-1]+'\n'+'\n'.join(zones)+'\n)\n'
  text=text.replace('(at 83 61)', '(at 83 77)').replace('(at 48 87)', '(at 54 91)')
  path.write_text(text)
  print('HF',name,len(parts),'parts',len(r.tracks),'tracks',len(r.vias),'vias',flush=True)
