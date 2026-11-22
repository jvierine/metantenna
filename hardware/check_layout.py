"""Independent geometric clearance and net connectivity checks on emitted routes.

This supplements, and does not replace, native KiCad DRC/ERC or RF bench tests.
"""
from pathlib import Path
from collections import defaultdict
import json
from shapely.geometry import box, Point, LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree

ROOT=Path(__file__).resolve().parents[1]

def geometry(a):
    items=[]
    for p in a['pads']:
        x,y,w,h=p['x'],p['y'],p['w'],p['h']
        g=Point(x,y).buffer(w/2,quad_segs=24) if p['drill'] else box(x-w/2,y-h/2,x+w/2,y+h/2)
        items.append((p['net'] or f"NC_{p['ref']}_{p['pin']}",g,[0,1] if p['drill'] else [0],p['ref']+'.'+p['pin']))
    for i,(n,l,p,q,w) in enumerate(a['tracks']):items.append((n,LineString([p,q]).buffer(w/2,quad_segs=8),[l],f'track{i}'))
    for i,(n,x,y) in enumerate(a['vias']):items.append((n,Point(x,y).buffer(.3,quad_segs=24),[0,1],f'via{i}'))
    return items

def check(name):
    a=json.loads((ROOT/'hardware'/f'{name}_layout.json').read_text());items=geometry(a)
    issues=[];minimum=10
    for layer in [0,1]:
        ii=[p for p in items if layer in p[2]];tree=STRtree([p[1] for p in ii])
        for i,(n,g,_,ref) in enumerate(ii):
            for j in tree.query(g.buffer(.2)):
                if j<=i or n==ii[j][0]:continue
                d=g.distance(ii[j][1]);minimum=min(minimum,d)
                if d<.149:issues.append([ref,ii[j][3],round(d,4),'F' if layer==0 else 'B'])
    # Verify all pads of every non-ground net form one copper component via
    # conductive plated through holes / vias. Ground planes are added at export.
    netitems=defaultdict(list)
    for n,g,ll,ref in items:
        if n!='GND' and not n.startswith('NC_'):netitems[n].append((g,ll,ref))
    for n,ii in netitems.items():
        seen={0};pending=[0]
        while pending:
            i=pending.pop()
            for j in range(len(ii)):
                if j not in seen and set(ii[i][1])&set(ii[j][1]) and ii[i][0].distance(ii[j][0])<1e-5:
                    seen.add(j);pending.append(j)
        if len(seen)!=len(ii):issues.append(['connectivity',n,len(ii)-len(seen)])
    w,h=a['size_mm']
    for p in a['pads']:
        if p['drill'] and min(p['w'],p['h'])/2-p['drill']/2<.24:issues.append(['annular ring',p['ref']])
    result={'board':name,'native_KiCad_DRC':'not yet run','geometric_minimum_copper_clearance_mm':round(minimum,4),'minimum_required_mm':.15,'issues':issues,'non_ground_nets_checked':len(netitems)}
    (ROOT/'manufacturing'/f'{name}_geometry_check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return not issues

if __name__=='__main__':
    good=[check(n) for n in ['preamp','biastee']]
    if not all(good):raise SystemExit(1)
