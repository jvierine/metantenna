"""Build editable KiCad PCB sources, routing and assembly workbooks.

All signal routing is on F.Cu. B.Cu is permitted only for DC/low-frequency
connections. In1.Cu is an uninterrupted RF reference except for anti-pads.
Native KiCad DRC and schematic comparison are separate release gates.
"""
from pathlib import Path
from collections import defaultdict
import json, math, heapq, uuid
import numpy as np
from shapely.geometry import box, Point, LineString
from shapely.ops import unary_union
from openpyxl import Workbook
from design import preamp,biastee

ROOT=Path(__file__).resolve().parents[1]
STEP=.2
CLEAR=.2
WIDTH=.32

def pads(pkg):
    # number, x, y, width, height, hole diameter (zero = SMT)
    if pkg in ['0805','1008','1206','2512','SOD323','SMA_DIODE']:
        pitch,w,h={'0805':(1.,1.2,1.4),'1008':(1.3,1.2,2.2),'1206':(1.5,1.6,1.8),'2512':(3.,2.,3.4),'SOD323':(1.15,1.,.9),'SMA_DIODE':(2.25,2.5,2.)}[pkg]
        return [('1',-pitch,0,w,h,0),('2',pitch,0,w,h,0)]
    if pkg=='SMA':return [('1',0,0,2.05,2.05,1.5)]+[('2',x,y,2.25,2.25,1.7) for x,y in [(2.54,2.54),(2.54,-2.54),(-2.54,-2.54),(-2.54,2.54)]]
    if pkg=='ANT_M3':return [('1',0,-43,4,4,1.5),('2',0,43,4,4,1.5)]
    if pkg=='TERM2':return [('1',-2.54,0,3,3,1.3),('2',2.54,0,3,3,1.3)]
    if pkg=='CD542':return [(str(i+1),-2.54,y,2.54,1.65,0) for i,y in enumerate([-2.54,0,2.54])]+[(str(i+4),2.54,y,2.54,1.65,0) for i,y in enumerate([2.54,0,-2.54])]
    if pkg=='SOT89':return [('1',-1.5,1.65,.9,1.3,0),('3',1.5,1.65,.9,1.3,0),('2',0,-.7375,1.733,3.125,0),('2',0,1.5625,.9,1.475,0)]
    if pkg=='MSOP8EP':return [(str(i+1),-2.15,-.975+i*.65,1.45,.4,0) for i in range(4)]+[(str(i+5),2.15,.975-i*.65,1.45,.4,0) for i in range(4)]+[('9',0,0,1.68,1.88,0)]
    raise ValueError(pkg)

def physical(part):
    # Positive board rotation follows KiCad's counter-clockwise convention.
    a=math.radians(part.rotation);c,s=math.cos(a),math.sin(a)
    out=[]
    for n,x,y,w,h,drill in pads(part.package):
        xx=part.x+c*x+s*y; yy=part.y-s*x+c*y
        if part.rotation%180: w,h=h,w
        g=Point(xx,yy).buffer(w/2,quad_segs=12) if drill else box(xx-w/2,yy-h/2,xx+w/2,yy+h/2)
        out.append(dict(ref=part.ref,pin=n,x=xx,y=yy,w=w,h=h,drill=drill,net=part.nets[n],shape=g))
    return out

class Router:
    def __init__(self,parts,size):
        self.size=size;self.pads=[p for c in parts for p in physical(c)]
        self.tracks=[];self.vias=[]
        self.nx=int(size[0]/STEP)+1;self.ny=int(size[1]/STEP)+1
        self.obstacles=[]
        for p in self.pads:
            self.obstacles.append((p['net'] or '__NC_'+p['ref']+p['pin'],p['shape'],[0,1] if p['drill'] else [0]))
        for x,y in [(6,6),(6,size[1]-6),(size[0]-6,6),(size[0]-6,size[1]-6)]:
            self.obstacles.append(('__HOLE',Point(x,y).buffer(1.8),[0,1]))
    def raster(self,net,width=WIDTH):
        a=np.zeros((2,self.nx,self.ny),dtype=bool)
        a[:,:4,:]=True;a[:,-4:,:]=True;a[:,:,:4]=True;a[:,:,-4:]=True
        for n,g,layers in self.obstacles:
            if n==net:continue
            g=g.buffer(CLEAR+width/2)
            x0,y0,x1,y1=g.bounds
            ix0=max(0,int(x0/STEP));ix1=min(self.nx-1,math.ceil(x1/STEP))
            iy0=max(0,int(y0/STEP));iy1=min(self.ny-1,math.ceil(y1/STEP))
            if ix0>ix1 or iy0>iy1:continue
            import shapely
            xx,yy=np.meshgrid(np.arange(ix0,ix1+1)*STEP,np.arange(iy0,iy1+1)*STEP,indexing='ij')
            inside=shapely.contains_xy(g,xx,yy)
            for layer in layers:a[layer,ix0:ix1+1,iy0:iy1+1]|=inside
        return a
    def connect(self,net,p,q,rf):
        width=WIDTH if rf else .2
        blocked=self.raster(net,width)
        start=(0,round(p[0]/STEP),round(p[1]/STEP));end=(0,round(q[0]/STEP),round(q[1]/STEP))
        if blocked[start] or blocked[end]:raise RuntimeError(('blocked pad',net,p,q))
        def heuristic(t):return abs(t[1]-end[1])+abs(t[2]-end[2])+20*t[0]
        heap=[(heuristic(start),0,start)];dist={start:0};prev={}
        while heap:
            _,d,u=heapq.heappop(heap)
            if d!=dist[u]:continue
            if u==end:break
            layer,x,y=u
            candidates=[((layer,x+dx,y+dy),1 if dx==0 or dy==0 else 1.4143) for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]]
            if not rf:candidates.append(((1-layer,x,y),30))
            for v,cost in candidates:
                ll,xx,yy=v
                if not (0<=xx<self.nx and 0<=yy<self.ny) or blocked[v]:continue
                if ll!=layer:
                    # A via needs a larger obstacle margin than a trace.
                    if any(n!=net and g.distance(Point(x*STEP,y*STEP))<.5 for n,g,_ in self.obstacles):continue
                    if any(not p['drill'] and p['shape'].distance(Point(x*STEP,y*STEP))<.4 for p in self.pads):continue
                nd=d+cost
                if nd<dist.get(v,float('inf')):
                    dist[v]=nd;prev[v]=u;heapq.heappush(heap,(nd+heuristic(v),nd,v))
        else:raise RuntimeError(('unrouted',net,p,q))
        route=[end]
        while route[-1]!=start:route.append(prev[route[-1]])
        route.reverse()
        points=[(0,*p)]+[(l,x*STEP,y*STEP) for l,x,y in route]+[(0,*q)]
        # Collapse collinear grid segments before emitting manufacturing geometry.
        compressed=[points[0]]
        for i in range(1,len(points)-1):
            a,b,c=compressed[-1],points[i],points[i+1]
            if a[0]==b[0]==c[0] and abs((b[1]-a[1])*(c[2]-b[2])-(b[2]-a[2])*(c[1]-b[1]))<1e-8:continue
            compressed.append(b)
        compressed.append(points[-1])
        for a,b in zip(compressed,compressed[1:]):
            if a[0]!=b[0]:
                self.vias.append((net,a[1],a[2]));self.obstacles.append((net,Point(a[1],a[2]).buffer(.3),[0,1]))
            elif math.dist(a[1:],b[1:])>1e-7:
                self.tracks.append((net,a[0],a[1:],b[1:],width));self.obstacles.append((net,LineString([a[1:],b[1:]]).buffer(width/2),[a[0]]))
    def antenna_feeds(self):
        """Explicit mirror-symmetric arm routes; Y crosses X on B.Cu.

        Two internal ground planes separate the crossing. Y changes layer
        adjacent to its transformer primary, outside the solder pads.
        """
        if not any(p['net']=='X_ANT_N' for p in self.pads):return set()
        def route(net,layer,points):
            for a,b in zip(points,points[1:]):
                self.tracks.append((net,layer,a,b,WIDTH))
                self.obstacles.append((net,LineString([a,b]).buffer(WIDTH/2),[layer]))
        for net,points,pad in [
            ('X_ANT_N',[(5,48),(8,48),(20,36),(45,36),(45.46,34.54)],(45.46,34.54)),
            ('X_ANT_P',[(91,48),(88,48),(76,36),(51,36),(50.54,34.54)],(50.54,34.54))]:
            route(net,0,points)
            route(net,0,[pad,(pad[0],39)])
        for net,points,yy in [
            ('Y_ANT_N',[(48,5),(15,5),(15,45.46),(27.7,45.46)],45.46),
            ('Y_ANT_P',[(48,91),(15,91),(15,50.54),(27.7,50.54)],50.54)]:
            route(net,1,points)
            self.vias.append((net,27.7,yy))
            self.obstacles.append((net,Point(27.7,yy).buffer(.3),[0,1]))
            route(net,0,[(26.5,yy),(29.46,yy)])
        return {'X_ANT_N','X_ANT_P','Y_ANT_N','Y_ANT_P'}

    def power_spine(self):
        """Keep the shared 12 V trunk on B.Cu, away from the RF ladder.

        Each F.Cu escape is local, with ordinary tented vias outside SMT pads.
        There are no digital signals or separate digital supply rails.
        """
        if not any(p['net']=='V12' for p in self.pads):return set()
        def track(layer,a,b,width=.4):
            self.tracks.append(('V12',layer,a,b,width))
            self.obstacles.append(('V12',LineString([a,b]).buffer(width/2),[layer]))
        def escape(ref,pin,via):
            pad=next(p for p in self.pads if p['ref']==ref and p['pin']==str(pin))
            track(0,(pad['x'],pad['y']),via)
            if ('V12',*via) not in self.vias:
                self.vias.append(('V12',*via))
                self.obstacles.append(('V12',Point(*via).buffer(.3),[0,1]))
            track(1,via,(85,via[1]))
        escape('D103',1,(79.5,38))
        escape('D104',1,(88,44.8))
        for base,dy in [(100,0),(200,40)]:
            escape(f'C{base+10}',1,(77.8,45+dy))
            escape(f'C{base+11}',1,(72,41.5+dy))
            escape(f'U{base+2}',8,(72,41.5+dy))
            escape(f'U{base+2}',5,(72,44.5+dy))
        track(1,(85,38),(85,85),.5)
        return {'V12'}

    def ground_vias(self):
        """Short, wide pad-to-plane connections without via-in-pad processing."""
        for p in self.pads:
            if p['net']!='GND' or p['drill']:continue
            center=(p['x'],p['y']);dx=p['w']/2+.6;dy=p['h']/2+.6
            offsets=[(sx*(dx+extra),sy*(dy+extra)) for extra in [0,.4,.8,1.2,1.8,2.4] for sx,sy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)]]
            count=0;wanted=2 if p['ref'].startswith('U') and p['pin'] in ['2','9'] else 1
            width=min(.8,p['w'],p['h'])
            for ox,oy in offsets:
                x,y=center[0]+ox,center[1]+oy;point=Point(x,y)
                if any(not a['drill'] and a['shape'].distance(point)<.4 for a in self.pads):continue
                if any(a['drill'] and math.dist((x,y),(a['x'],a['y']))<a['drill']/2+.15+.25 for a in self.pads):continue
                if any(n!='GND' and g.distance(point)<.51 for n,g,_ in self.obstacles):continue
                stub=LineString([center,(x,y)]).buffer(width/2)
                if any(n!='GND' and 0 in ll and g.distance(stub)<.15 for n,g,ll in self.obstacles):continue
                if any(math.dist((x,y),(xx,yy))<.7 for _,xx,yy in self.vias):continue
                self.tracks.append(('GND',0,center,(x,y),width))
                self.obstacles.append(('GND',stub,[0]))
                self.vias.append(('GND',x,y));count+=1
                self.obstacles.append(('GND',point.buffer(.3),[0,1]))
                if count==wanted:break
            if not count:raise RuntimeError(('ground via clearance',p['ref'],p['pin']))

    def ground_fence(self):
        """Low-cost through-via stitching: perimeter, RF regions and transitions."""
        w,h=self.size
        points=[(x,y) for x in np.arange(2,w-1,5) for y in [2,h-2]]
        points += [(x,y) for y in np.arange(7,h-2,5) for x in [2,w-2]]
        if w==96:
            points += [(18,y) for y in np.arange(10,87,4)]
            points += [(x,y) for x in np.arange(23,90,5) for y in [24,58,72]]
            points += [(27.7,y) for y in [44,46.9,49.1,52]]
        for x,y in points:
            point=Point(x,y)
            if any(not a['drill'] and a['shape'].distance(point)<.4 for a in self.pads):continue
            if any(a['drill'] and math.dist((x,y),(a['x'],a['y']))<a['drill']/2+.15+.25 for a in self.pads):continue
            if any(n!='GND' and g.distance(point)<.51 for n,g,_ in self.obstacles):continue
            if any(math.dist((x,y),(xx,yy))<.7 for _,xx,yy in self.vias):continue
            self.vias.append(('GND',float(x),float(y)))
            self.obstacles.append(('GND',point.buffer(.3),[0,1]))

    def run(self):
        completed=self.antenna_feeds()|self.power_spine()
        self.ground_vias()
        groups=defaultdict(list)
        for p in self.pads:
            if p['net'] and p['net']!='GND' and p['net'] not in completed:groups[p['net']].append((p['x'],p['y']))
        def rf(n):return not any(n.endswith('_'+s) for s in ['RAW','V12','V8','FB','NR','BIAS','DC']) and n not in ['VIN','VIN_FUSED','PROTECTED','V12']
        for n,points in sorted(groups.items(),key=lambda a:(not rf(a[0]),not a[0].endswith(('_FB','_NR')),-len(a[1]))):
            tree=[points.pop(0)]
            while points:
                _,i,a,b=min((math.dist(a,b),i,a,b) for i,b in enumerate(points) for a in tree)
                self.connect(n,a,b,rf(n));tree.append(points.pop(i))
        self.ground_fence()
        return self

def q(s):return json.dumps(str(s))
def pcb(name,parts,size,r):
    nets={'GND':1}
    for p in parts:
        for n in p.nets.values():
            if n and n not in nets:nets[n]=len(nets)+1
    lines=['(kicad_pcb (version 20221018) (generator pcbnew)', '(general (thickness 1.6))','(paper "A4")',
           '(layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" power) (31 "B.Cu" signal) (32 "B.Adhes" user "B.Adhesive") (33 "F.Adhes" user "F.Adhesive") (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen") (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user) (46 "B.CrtYd" user "B.Courtyard") (47 "F.CrtYd" user "F.Courtyard") (48 "B.Fab" user) (49 "F.Fab" user))',
           '(setup (pad_to_mask_clearance 0.05))','(net 0 "")']
    nc={}
    for p in parts:
        for pin,n in p.nets.items():
            if not n:
                label={'3':'NC-','7':'DNC-'}.get(pin,'') if p.package=='MSOP8EP' else ''
                nn=f'unconnected-({p.ref}-{label}Pad{pin})'
                nc[(p.ref,pin)]=nn;nets[nn]=len(nets)+1
    native_name=lambda n:n if n.startswith('unconnected-') else '/'+n
    lines += [f'(net {i} {q(native_name(n))})' for n,i in nets.items()]
    for p in parts:
        lines.append(f'(footprint {q("metantenna:"+p.package)} (layer "{p.side}.Cu") (at {p.x} {p.y} {p.rotation}) (attr {"through_hole" if p.package in ["SMA","ANT_M3","TERM2"] else "smd"}{" dnp" if p.value.startswith("DNP") else ""})')
        lines.append(f'(fp_text reference {q(p.ref)} (at 0 -3.5) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))')
        lines.append(f'(fp_text value {q(p.value)} (at 0 0) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.1))))')
        for pin,x,y,w,h,hole in pads(p.package):
            n=p.nets[pin] or nc[(p.ref,pin)];net=f'(net {nets[n]} {q(native_name(n))})'
            typ='thru_hole' if hole else 'smd';shape='circle' if hole else 'rect'
            layers='"*.Cu" "*.Mask"' if hole else ('"F.Cu" "F.Mask"' if p.package=='MSOP8EP' and pin=='9' else '"F.Cu" "F.Paste" "F.Mask"')
            drill=f'(drill {hole})' if hole else ''
            lines.append(f'(pad {q(pin)} {typ} {shape} (at {x} {y} {p.rotation}) (size {w} {h}) {drill} (layers {layers}) {net})')
        if p.package=='MSOP8EP':
            for dx in [-.42,.42]:
                for dy in [-.47,.47]:
                    lines.append(f'(pad "" smd rect (at {dx} {dy}) (size .68 .76) (layers "F.Paste"))')
        lines.append(')')
    for i,(x,y) in enumerate([(6,6),(6,size[1]-6),(size[0]-6,6),(size[0]-6,size[1]-6)]):
        lines.append(f'(footprint "metantenna:MountingHole" (layer "F.Cu") (at {x} {y}) (attr board_only exclude_from_pos_files exclude_from_bom) (fp_text reference "H{i+1}" (at 0 -3) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15)))) (pad "" np_thru_hole circle (at 0 0) (size 3.2 3.2) (drill 3.2) (layers "*.Cu" "*.Mask")))')
    labels=([(20,6,'METANTENNA B0'),(83,21,'X RF+12V'),(83,61,'Y RF ONLY'),(5,44.5,'X-'),(91,52,'X+'),(48,9,'Y-'),(48,87,'Y+')] if name=='preamp' else [(40,60,'METANTENNA B0'),(17,32,'X ANT+DC'),(62,32,'X RX'),(17,55,'Y ANT'),(62,55,'Y RX'),(37.46,4,'+12V'),(44,4,'GND')])
    for x,y,label in labels:
        lines.append(f'(gr_text {q(label)} (at {x} {y}) (layer "F.SilkS") (effects (font (size .8 .8) (thickness .12))))')
    for n,l,a,b,width in r.tracks:
        lines.append(f'(segment (start {a[0]:.4f} {a[1]:.4f}) (end {b[0]:.4f} {b[1]:.4f}) (width {width}) (layer "{["F.Cu","B.Cu"][l]}") (net {nets[n]}))')
    for n,x,y in r.vias:lines.append(f'(via (at {x:.4f} {y:.4f}) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net {nets[n]}))')
    w,h=size
    for a,b in [((0,0),(w,0)),((w,0),(w,h)),((w,h),(0,h)),((0,h),(0,0))]:
        lines.append(f'(gr_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width 0.05) (type default)) (layer "Edge.Cuts"))')
    for layer in ['F.Cu','In1.Cu','In2.Cu','B.Cu']:
        clearance=.5 if layer in ['F.Cu','B.Cu'] else .25
        lines.append(f'(zone (net 1) (net_name "/GND") (layer "{layer}") (hatch edge 0.5) (connect_pads yes (clearance {clearance})) (min_thickness 0.25) (fill yes (thermal_gap 0.25) (thermal_bridge_width 0.3)) (polygon (pts (xy 0.5 0.5) (xy {w-.5} 0.5) (xy {w-.5} {h-.5}) (xy 0.5 {h-.5}))))')
    lines.append(')')
    lib=ROOT/'hardware/metantenna.pretty';lib.mkdir(exist_ok=True)
    for pkg in {p.package for p in parts}|{'MountingHole'}:
        fp=[f'(footprint "{pkg}" (version 20221018) (generator pcbnew) (layer "F.Cu")']
        fp.append('(attr '+('board_only exclude_from_pos_files exclude_from_bom' if pkg=='MountingHole' else ('through_hole' if pkg in ['SMA','ANT_M3','TERM2'] else 'smd'))+')')
        if pkg=='MountingHole':fp.append('(pad "" np_thru_hole circle (at 0 0) (size 3.2 3.2) (drill 3.2) (layers "*.Cu" "*.Mask"))')
        else:
            for pin,x,y,ww,hh,hole in pads(pkg):
                typ='thru_hole' if hole else 'smd';shape='circle' if hole else 'rect'
                layers='"*.Cu" "*.Mask"' if hole else ('"F.Cu" "F.Mask"' if pkg=='MSOP8EP' and pin=='9' else '"F.Cu" "F.Paste" "F.Mask"')
                drill=f'(drill {hole})' if hole else ''
                fp.append(f'(pad "{pin}" {typ} {shape} (at {x} {y}) (size {ww} {hh}) {drill} (layers {layers}))')
        if pkg=='MSOP8EP':
            for dx in [-.42,.42]:
                for dy in [-.47,.47]:fp.append(f'(pad "" smd rect (at {dx} {dy}) (size .68 .76) (layers "F.Paste"))')
        (lib/f'{pkg}.kicad_mod').write_text('\n'.join(fp)+')\n')
    (ROOT/'hardware/fp-lib-table').write_text('(fp_lib_table (lib (name "metantenna") (type "KiCad") (uri "${KIPRJMOD}/metantenna.pretty") (options "") (descr "Metantenna custom lands")))\n')
    (ROOT/'hardware'/f'{name}.kicad_pcb').write_text('\n'.join(lines)+'\n')
    dump={'size_mm':size,'parts':[dict(ref=p.ref,value=p.value,package=p.package,nets=p.nets,x=p.x,y=p.y,rotation=p.rotation,side=p.side,mpn=p.mpn,note=p.note) for p in parts], 'pads':[{k:v for k,v in p.items() if k!='shape'} for p in r.pads],'tracks':r.tracks,'vias':r.vias}
    (ROOT/'hardware'/f'{name}_layout.json').write_text(json.dumps(dump,indent=2)+'\n')
    wb=Workbook();s=wb.active;s.title='BOM';s.append(['Designator','Value','Footprint','Quantity','Manufacturer Part','Assembly notes'])
    for p in parts:s.append([p.ref,p.value,p.package,1,p.mpn,p.note])
    s=wb.create_sheet('Placement');s.append(['Designator','Mid X (mm)','Mid Y (mm)','Layer','Rotation'])
    for p in parts:s.append([p.ref,p.x,-p.y,'Top' if p.side=='F' else 'Bottom',p.rotation])
    for sheet in wb:
        sheet.freeze_panes='A2'
        for col in sheet.columns:sheet.column_dimensions[col[0].column_letter].width=min(70,max(12,max(len(str(c.value or '')) for c in col)+2))
    wb.save(ROOT/'manufacturing'/f'{name}_assembly.xlsx')

def main():
    for name,fn in [('preamp',preamp),('biastee',biastee)]:
        parts,size=fn();r=Router(parts,size).run();pcb(name,parts,size,r)
        print(name,len(parts),'parts;',len(r.tracks),'segments;',len(r.vias),'vias',flush=True)

if __name__=='__main__':main()
