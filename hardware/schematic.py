"""Generate self-contained KiCad schematics from the electrical source of truth.

Named nets connect the functional component groups. Pin numbers match PCB pads.
"""
from pathlib import Path
import json,uuid
from design import preamp,biastee

ROOT=(Path(__file__).resolve().parents[1]/"vhf")
def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'metantenna/'+s))
def q(s):return json.dumps(str(s))
def effects(size=1.0,extra=''):return f'(effects (font (size {size} {size})) {extra})'
def line(a,b):return f'(polyline (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0.2) (type default)) (fill (type none)))'

def pins(p):
    if p.package in ['ACM7060','ACM4520']:return [('1',-7.62,2.54,0),('2',-7.62,-2.54,0),('3',7.62,-2.54,180),('4',7.62,2.54,180)]
    if len(p.nets)==2:return [('1',-5.08,0,0),('2',5.08,0,180)]
    if p.package=='SOT89':return [('1',-7.62,0,0),('3',7.62,0,180),('2',0,-7.62,90)]
    if p.package=='CD542':return [('1',-7.62,2.54,0),('3',-7.62,-2.54,0),('4',7.62,-2.54,180),('6',7.62,2.54,180),('2',-2.54,-7.62,90),('5',2.54,-7.62,90)]
    return [(str(i+1),-7.62,3.81-2.54*i,0) for i in range(4)]+[(str(i+5),7.62,-3.81+2.54*i,180) for i in range(4)]+[('9',0,-10.16,90)]

def build(name,parts):
    if name=="preamp" and ROOT==Path(__file__).resolve().parents[1]/"vhf":
        from hierarchical_schematic import build as hierarchical_build
        hierarchical_build();return
    rootid=uid(name);lines=[f'(kicad_sch (version 20231120) (generator "eeschema") (uuid "{rootid}") (paper "A2")',
        f'(title_block (title {q("Metantenna — "+name+" — engineering prototype")}) (date "2026-11-23") (rev "B0") (company "Juha Vierinen"))','(lib_symbols']
    for p in parts:
        lib=p.ref
        lines.append(f'(symbol "metantenna:{lib}" (pin_names (offset 0.5)) (in_bom yes) (on_board yes)')
        lines += [f'(property "Reference" {q(p.ref[0])} (at 0 10.16 0) {effects()})',f'(property "Value" {q(p.value)} (at 0 7.62 0) {effects()})',f'(property "Footprint" {q("metantenna:"+p.package)} (at 0 0 0) {effects(extra="hide")})']
        shapes=[]
        if len(p.nets)==2 and p.ref[0]=='C':
            shapes=[line((-2.54,0),(-.6,0)),line((-.6,-2),(-.6,2)),line((.6,-2),(.6,2)),line((.6,0),(2.54,0))]
        elif p.package=='SOT89':
            shapes=[f'(polyline (pts (xy -5.08 -4) (xy -5.08 4) (xy 5.08 0) (xy -5.08 -4)) (stroke (width 0.2) (type default)) (fill (type background)))',line((0,-5.08),(0,-2))]
        else:
            half=2.54 if len(p.nets)==2 else 5.08
            shapes=[f'(rectangle (start {-half} -5.08) (end {half} 5.08) (stroke (width 0.2) (type default)) (fill (type background)))']
        lines.append(f'(symbol "{lib}_0_1" '+''.join(shapes)+')')
        lines.append(f'(symbol "{lib}_1_1"')
        for pin,x,y,angle in pins(p):
            label={'SOT89':{'1':'IN','2':'GND','3':'OUT/DC'},'MSOP8EP':{'1':'OUT','2':'FB','3':'NC','4':'GND','5':'EN','6':'NR/SS','7':'DNC','8':'IN','9':'EP'}}.get(p.package,{}).get(pin,'~')
            lines.append(f'(pin passive line (at {x} {y} {angle}) (length 2.54) (name {q(label)} {effects(.8)}) (number {q(pin)} {effects(.8)}))')
        lines.append('))')
    lines.append(')')
    for k,p in enumerate(parts):
        x=34+(k%9)*62;y=30+(k//9)*46;partid=uid(name+'/'+p.ref)
        lines.append(f'(symbol (lib_id "metantenna:{p.ref}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp {"yes" if p.value.startswith("DNP") else "no"}) (uuid "{partid}")')
        lines.extend([f'(property "Reference" {q(p.ref)} (at {x} {y-15} 0) {effects(1.2)})',f'(property "Value" {q(p.value)} (at {x} {y-12.5} 0) {effects(1.1)})',f'(property "Footprint" {q("metantenna:"+p.package)} (at {x} {y} 0) {effects(extra="hide")})',f'(property "MPN" {q(p.mpn)} (at {x} {y} 0) {effects(extra="hide")})'])
        for pin,*_ in pins(p):lines.append(f'(pin {q(pin)} (uuid "{uid(name+p.ref+pin)}"))')
        lines.append(f'(instances (project "{name}" (path "/{rootid}" (reference {q(p.ref)}) (unit 1)))) )')
        for pin,px,py,angle in pins(p):
            xx=x+px;yy=y-py;n=p.nets[pin]
            if not n:
                lines.append(f'(no_connect (at {xx} {yy}) (uuid "{uid(name+p.ref+pin+"NC")}"))');continue
            dx=-3.81 if angle==0 else (3.81 if angle==180 else 0)
            dy=3.81 if angle==90 else 0
            ex,ey=xx+dx,yy+dy
            lines.append(f'(wire (pts (xy {xx} {yy}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(name+p.ref+pin+"wire")}"))')
            align='(justify right bottom)' if dx<0 else '(justify left bottom)'
            lines.append(f'(label {q(n)} (at {ex} {ey} 0) {effects(.9,align)} (uuid "{uid(name+p.ref+pin+"label")}"))')
    lines.append(')')
    (ROOT/'hardware'/f'{name}.kicad_sch').write_text('\n'.join(lines)+'\n')
    proj={'board':{'design_settings':{'rules':{'min_clearance':.15,'min_track_width':.2,'min_via_diameter':.6,'min_through_hole_diameter':.3,'min_hole_to_hole':.25}}},'net_settings':{'classes':[{'name':'Default','clearance':.15,'track_width':.32,'via_diameter':.6,'via_drill':.3,'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.2,'diff_pair_gap':.25,'diff_pair_via_gap':.25,'wire_width':6,'bus_width':12,'line_style':0,'pcb_color':'rgba(0, 0, 0, 0.000)','schematic_color':'rgba(0, 0, 0, 0.000)'}],'meta':{'version':3}},'meta':{'filename':name+'.kicad_pro','version':1}}
    (ROOT/'hardware'/f'{name}.kicad_pro').write_text(json.dumps(proj,indent=2)+'\n')

if __name__=='__main__':
    for name,fn in [('preamp',preamp),('biastee',biastee)]:build(name,fn()[0])
