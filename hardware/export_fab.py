"""Export RS-274X Gerber, Excellon, assembly drawings and prototype ZIPs.

Geometric checks must pass before export. These are prototype CAM files;
independent manufacturer CAM review and native KiCad DRC are release gates.
"""
from pathlib import Path
import json,zipfile,hashlib
import numpy as np
from PIL import ImageFont
from shapely.geometry import Polygon,Point,box,LineString
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
from check_layout import check,geometry

ROOT=Path(__file__).resolve().parents[1]
def regions(g):
    if g.is_empty:return []
    if isinstance(g,Polygon):
        if g.interiors:return list(constrained_delaunay_triangles(g).geoms)
        return [g]
    return [p for c in g.geoms for p in regions(c)]

def gerber(path,shapes,role):
    s=['G04 Metantenna engineering prototype*','%FSLAX46Y46*%','%MOMM*%','%LPD*%','%ADD10C,0.010*%','D10*']
    for g in shapes:
        for poly in regions(g):
            xy=list(poly.exterior.coords)
            if len(xy)<4:continue
            s.append('G36*')
            for i,(x,y) in enumerate(xy):
                s.append(f'X{round(x*1e6):010d}Y{round(-y*1e6):+011d}D{2 if i==0 else 1:02d}*')
            s.append('G37*')
    s.extend(['M02*','']);path.write_text('\n'.join(s))

def outline(path,w,h):
    s=['G04 Board outline*','%FSLAX46Y46*%','%MOMM*%','%ADD10C,0.050*%','D10*']
    for i,(x,y) in enumerate([(0,0),(w,0),(w,-h),(0,-h),(0,0)]):s.append(f'X{round(x*1e6):010d}Y{round(y*1e6):+011d}D{2 if i==0 else 1:02d}*')
    path.write_text('\n'.join(s+['M02*','']))

def drill(path,holes):
    sizes=sorted({round(d,3) for x,y,d in holes});s=['M48',';TYPE=PLATED' if 'PTH.' in path.name and 'NPTH' not in path.name else ';TYPE=NON_PLATED','METRIC,TZ']
    s += [f'T{i+1:02d}C{d:.3f}' for i,d in enumerate(sizes)];s+=['%','G90','G05']
    for i,d in enumerate(sizes):
        s.append(f'T{i+1:02d}')
        s += [f'X{x:.4f}Y{-y:.4f}' for x,y,dd in holes if round(dd,3)==d]
    path.write_text('\n'.join(s+['M30','']))

def silk(text,x,y):
    font=ImageFont.load_default(size=12)
    a=np.array(font.getmask(text)).reshape((font.getmask(text).size[1],font.getmask(text).size[0]))
    return unary_union([box(x+j*.12,y+i*.12,x+(j+1)*.12,y+(i+1)*.12) for i,j in zip(*np.where(a>80))])

def svg(name,a):
    w,h=a['size_mm'];scale=7
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w*scale}" height="{h*scale}" viewBox="-2 -2 {w+4} {h+4}">',f'<rect x="0" y="0" width="{w}" height="{h}" rx="1" fill="#f7faf8" stroke="#263b35" stroke-width=".25"/>']
    for n,l,p,q,ww in a['tracks']:
        s.append(f'<path d="M {p[0]} {p[1]} L {q[0]} {q[1]}" stroke="{["#b52a32","#3065ab"][l]}" stroke-width="{ww}"/>')
    for p in a['pads']:
        if p['drill']:s.append(f'<circle cx="{p["x"]}" cy="{p["y"]}" r="{p["w"]/2}" fill="#d7b45a"/><circle cx="{p["x"]}" cy="{p["y"]}" r="{p["drill"]/2}" fill="white"/>')
        else:s.append(f'<rect x="{p["x"]-p["w"]/2}" y="{p["y"]-p["h"]/2}" width="{p["w"]}" height="{p["h"]}" fill="#d7b45a"/>')
    for n,x,y in a['vias']:s.append(f'<circle cx="{x}" cy="{y}" r=".3" fill="#c7a75a"/><circle cx="{x}" cy="{y}" r=".15" fill="white"/>')
    # Place assembly references clear of copper pads and other labels.
    occupied=[box(p['x']-p['w']/2-.25,p['y']-p['h']/2-.25,p['x']+p['w']/2+.25,p['y']+p['h']/2+.25) for p in a['pads']]
    occupied += [LineString([p,q]).buffer(ww/2+.25) for n,l,p,q,ww in a['tracks']]
    if name=='preamp':
        occupied += [box(74,17,94,22),box(74,57,94,62)]
    if name=='biastee':occupied += [box(54,31.5,75,35)]
    for p in [p for p in a['parts'] if p['package']!='ANT_M3']:
        tw=len(p['ref'])*.8;pos=None
        for radius in [3.4,4.5,6,8,10,12]:
            for dx,dy in [(0,-1),(0,1),(-1,0),(1,0),(-1,-1),(1,-1),(-1,1),(1,1)]:
                x,y=p['x']+dx*radius,p['y']+dy*radius
                rect=box(x-tw/2-.2,y-1.35,x+tw/2+.2,y+.25)
                if rect.bounds[0]<1 or rect.bounds[1]<1 or rect.bounds[2]>w-1 or rect.bounds[3]>h-1:continue
                if any(rect.intersects(g) for g in occupied):continue
                pos=(x,y,rect);break
            if pos:break
        if pos is None:raise RuntimeError(('assembly label cannot fit',p['ref']))
        x,y,rect=pos;occupied.append(rect)
        if abs(x-p['x'])+abs(y-p['y'])>5:
            s.append(f'<path d="M {p["x"]} {p["y"]} L {x} {y-.5}" stroke="#8b9d98" stroke-width=".12" fill="none"/>')
        s.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-family="sans-serif" font-size="1.25" fill="#182c25">{p["ref"]}</text>')
    for p in a['pads']:
        if p['pin']=='1' and p['ref'].startswith(('U','T','D','CM')):
            s.append(f'<text x="{p["x"]}" y="{p["y"]+.25}" text-anchor="middle" font-family="sans-serif" font-size=".65" font-weight="bold" fill="#482f00">1</text>')
    for x,y in [(6,6),(6,h-6),(w-6,6),(w-6,h-6)]:s.append(f'<circle cx="{x}" cy="{y}" r="1.6" fill="white" stroke="#444" stroke-width=".1"/>')
    labels = [(48,3,'Y−'),(48,95,'Y+'),(5,45,'X−'),(91,45,'X+'),(83,20,'X RF + 12 V'),(83,60,'Y RF only')] if name=='preamp' else [(10,20,'X antenna + DC'),(65,34,'X receiver'),(10,57,'Y antenna'),(65,57,'Y receiver'),(40,4,'12 V input')]
    for x,y,label in labels:
        s.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-family="sans-serif" font-size="1.8" font-weight="bold" fill="#182c25">{label}</text>')
    s.append('</svg>');(ROOT/'docs'/f'{name}_layout.svg').write_text('\n'.join(s))

def main():
    for name in ['preamp','biastee']:
        assert check(name),'Refusing export with geometric violations'
        a=json.loads((ROOT/'hardware'/f'{name}_layout.json').read_text());items=geometry(a);w,h=a['size_mm']
        out=ROOT/'manufacturing'/name;out.mkdir(exist_ok=True)
        mount=[(6,6,3.2),(6,h-6,3.2),(w-6,6,3.2),(w-6,h-6,3.2)]
        holes=[(p['x'],p['y'],p['drill']) for p in a['pads'] if p['drill']]+[(x,y,.3) for _,x,y in a['vias']]
        bounds=box(.5,.5,w-.5,h-.5)
        islands=[]
        if name=='biastee':
            bounds-=box(34,0,50,14)
            for prefix,y in [('X',27),('Y',50)]:
                bounds-=box(0,y-8,15.5,y+8)
                islands.append((prefix+'_ANT_RETURN',box(.5,y-7,12.4,y+7)))
        for layer,label in [(0,'F_Cu'),(1,'B_Cu')]:
            shapes=[g for n,g,ll,_ in items if layer in ll]
            if layer in [0,1]:
                for net,area in [('GND',bounds)]+islands:
                    cuts=[g.buffer(.5) for n,g,ll,_ in items if layer in ll and n!=net]+[Point(x,y).buffer(d/2+.25) for x,y,d in mount]
                    shapes.append(area-unary_union(cuts))
            gerber(out/f'{name}-{label}.gbr',shapes,label)
        for label in ['In1_Cu','In2_Cu']:
            cuts=[Point(p['x'],p['y']).buffer(p['w']/2+.25,quad_segs=24) for p in a['pads'] if p['drill'] and p['net']!='GND']
            cuts += [Point(x,y).buffer(.55,quad_segs=24) for n,x,y in a['vias'] if n!='GND']+[Point(x,y).buffer(d/2+.25) for x,y,d in mount]
            shapes=[bounds-unary_union(cuts)]
            for net,area in islands:
                icuts=[Point(p['x'],p['y']).buffer(p['w']/2+.25,quad_segs=24) for p in a['pads'] if p['drill'] and p['net']!=net]+[Point(x,y).buffer(.55) for n,x,y in a['vias'] if n!=net]+[Point(x,y).buffer(d/2+.25) for x,y,d in mount]
                shapes.append(area-unary_union(icuts))
            gerber(out/f'{name}-{label}.gbr',shapes,label)
        masks=[]
        for layer,label in [(0,'F_Mask'),(1,'B_Mask')]:
            shapes=[g.buffer(.05,join_style=2) for n,g,ll,ref in items if layer in ll and not ref.startswith(('track','via'))]
            gerber(out/f'{name}-{label}.gbr',shapes,label)
            if layer==0:masks=shapes
        paste=[]
        for p in a['pads']:
            if p['drill']:continue
            if p['pin']=='9':
                paste.extend(box(p['x']+dx-.34,p['y']+dy-.38,p['x']+dx+.34,p['y']+dy+.38) for dx in [-.42,.42] for dy in [-.47,.47])
            else:paste.append(box(p['x']-p['w']/2,p['y']-p['h']/2,p['x']+p['w']/2,p['y']+p['h']/2))
        gerber(out/f'{name}-F_Paste.gbr',paste,'F_Paste')
        marking=silk('METANTENNA '+name.upper()+' B0',12,3)
        for p in a['parts']:marking=marking.union(silk(p['ref'],p['x']-1.3,p['y']-4))
        marking-=unary_union(masks).buffer(.1)
        gerber(out/f'{name}-F_Silkscreen.gbr',[marking],'F_Silkscreen')
        outline(out/f'{name}-Edge_Cuts.gbr',w,h)
        drill(out/f'{name}-PTH.drl',holes);drill(out/f'{name}-NPTH.drl',mount)
        with zipfile.ZipFile(ROOT/'manufacturing'/f'{name}_prototype_gerbers.zip','w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(out.iterdir()):z.write(p,p.name)
        svg(name,a)
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'manufacturing').rglob('*') if p.is_file() and p.name!='sha256.json'}
    (ROOT/'manufacturing/sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':main()
