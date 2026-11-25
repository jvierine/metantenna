"""Place assembly designators beside footprints and outside solder openings."""
from pathlib import Path
import math

import sexpdata as sx
from shapely.geometry import Point, box

HERE = Path(__file__).resolve().parent


def children(item, tag):
    return [v for v in item if isinstance(v, list) and v and str(v[0]) == tag]


def field(item, tag):
    return children(item, tag)[0]


def text_box(label, x, y, height):
    w = .43 * height * len(label) + .12
    h = .65 * height + .12
    return box(x-w, y-h, x+w, y+h)


def add_labels(path):
    tree = sx.loads(path.read_text())
    # Strip only the generated reference texts, preserving all connector legends.
    footprints = []
    for fp in children(tree, 'footprint'):
        ref = next(t[2] for t in children(fp, 'fp_text') if str(t[1]) == 'reference')
        if ref.startswith('H') or 'ANT_M3' in fp[1]:
            continue
        footprints.append((ref, fp))
    refs = {ref for ref, _ in footprints}
    tree = [item for item in tree if not (isinstance(item, list) and item
            and str(item[0]) == 'gr_text' and item[1] in refs)]
    size_x, size_y = (96, 96) if path.stem == 'preamp' else (76,64)
    printable = box(.8, .8, size_x-.8, size_y-.8)
    obstacles = []
    for item in children(tree,'gr_text'):
        x,y = field(item,'at')[1:3]
        height = field(field(field(item,'effects'),'font'),'size')[1]
        obstacles.append(text_box(item[1],x,y,height))
    for item in children(tree,'gr_poly'):
        pts=[p[1:] for p in field(item,'pts')[1:]]
        obstacles.append(box(min(p[0] for p in pts), min(p[1] for p in pts),
                             max(p[0] for p in pts), max(p[1] for p in pts)).buffer(.2))
    pads_by_ref = {}
    for x in (6., size_x-6):
        for y in (3., size_y-9):
            obstacles.append(text_box("H4", x, y, 1.0).buffer(.3))
    for fp in children(tree,'footprint'):
        ref=next(t[2] for t in children(fp,'fp_text') if str(t[1])=='reference')
        x,y,*rot=field(fp,'at')[1:]
        a=math.radians(rot[0] if rot else 0)
        bounds=[]
        for p in children(fp,'pad'):
            px,py=field(p,'at')[1:3]
            u=x+math.cos(a)*px+math.sin(a)*py
            v=y-math.sin(a)*px+math.cos(a)*py
            w,h=field(p,'size')[1:3]
            if rot and rot[0]%180==90:
                w,h=h,w
            bounds.append((u-w/2,v-h/2,u+w/2,v+h/2))
        if not bounds:
            continue
        extent=box(min(p[0] for p in bounds),min(p[1] for p in bounds),
                   max(p[2] for p in bounds),max(p[3] for p in bounds))
        if ref in ('J102','J202'):
            extent=Point(x,y).buffer(6)
        elif ref in ('J10','J11','J20','J21'):
            extent=box(x-3.5,y-3.7,x+3.5,y+3.7)
        elif ref=='J1' and path.stem=='biastee':
            extent=box(x-5.5,y-5.1,x+5.5,y+5.1)
        pads_by_ref[ref]=extent
        obstacles.append(extent.buffer(.20))
    placed=[]
    for ref,fp in sorted(footprints,key=lambda row: pads_by_ref[row[0]].area,reverse=True):
        x,y=field(fp,'at')[1:3]
        candidates=[]
        for ring in range(3,39):
            r=.3*ring
            for angle in range(0,360,15):
                a=math.radians(angle)
                xx,yy=x+r*math.cos(a),y+r*math.sin(a)
                b=text_box(ref,xx,yy,.85)
                if not printable.contains(b) or any(b.intersects(o) for o in obstacles):
                    continue
                distance=b.distance(pads_by_ref[ref])
                candidates.append((distance+.07*r,xx,yy,b))
            if candidates and ring>25:
                break
        if not candidates:
            raise ValueError((path,ref,'no clear silkscreen placement'))
        _,xx,yy,b=min(candidates,key=lambda v:v[0])
        obstacles.append(b)
        tree.append(sx.loads(f'(gr_text "{ref}" (at {xx:.3f} {yy:.3f}) (layer "F.SilkS") '
                             '(effects (font (size 0.85 0.85) (thickness 0.13))))'))
        placed.append(ref)
    path.write_text('('+str(tree[0])+'\n'+'\n'.join(sx.dumps(q) for q in tree[1:])+'\n)\n')
    print(f'{path.stem}: {len(placed)} reference markings')


if __name__ == '__main__':
    for name in ('preamp','biastee'):
        add_labels(HERE/'hardware'/f'{name}.kicad_pcb')
