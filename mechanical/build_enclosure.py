"""Parametric manifold CSG housing; export watertight STL for Bambu Studio.

All dimensions in mm. The printed enclosure is ventilated/rain-shedding, not
hermetic or IP rated. Pipe and fastener clearances must be fit-tested first.
"""
from pathlib import Path
import json
import numpy as np
import manifold3d as m
import trimesh

ROOT=Path(__file__).resolve().parent
P=json.loads((ROOT/'config.json').read_text())
M=m.Manifold

def box(x,y,z,cx=0,cy=0,cz=0): return M.cube((x,y,z),center=True).translate((cx,cy,cz+z/2))
def cyl(r,h,x=0,y=0,z=0): return M.cylinder(h,r,circular_segments=96).translate((x,y,z))
def hole_y(r,length,x,y,z): return M.cylinder(length,r,circular_segments=48).rotate((90,0,0)).translate((x,y,z))

def parts():
    w,d=P['base_width_mm'],P['base_depth_mm']
    base=box(w,d,35)-box(w-6,d-6,40,cz=3)
    # Four M3 PCB mounts: 2.7 mm pilots for thread-forming screws in ASA.
    for x,y in P['pcb_hole_centers_mm']:
        base+=cyl(4.5,15,x,y)
        base-=cyl(1.35,13,x,y,3)
    # Board mounting datum and actual SMA coordinates are shared with PCB generator.
    for x,y in P['sma_centers_mm']: base-=cyl(7.5,8,x,y,-2)
    # Downward-open rain well; shields both connector nuts, permits drainage.
    well=box(34,76,27,42,-2,-27)-box(29,71,30,42,-2,-28)
    well+=box(46,84,3,42,-2,-3)-box(29,71,5,42,-2,-4)
    for x in [22,62]:
        for y in [-40,36]:
            well-=cyl(1.7,7,x,y,-5)
            base-=cyl(1.35,5,x,y,-1)
    # Base drainage holes sit beneath the hood's 15 mm overlap.
    for x in [-52,52]:
        for y in [-51,51]: base-=cyl(1.5,8,x,y,-2)
    # M8 cable gland entries (matched short balanced feed leads).
    for x in [-20,20]:
        for y in [-51,51]: base-=cyl(4.1,7,x,y,-1)
    # Structural suspension ears attach to the base, never the removable lid.
    for x in [-68,68]:
        for y in [-43,43]:
            ear=box(18,16,7,x,y,0)+cyl(8,7,x+(-4 if x<0 else 4),y)
            base+=ear
            base-=cyl(2.7,10,x+(-4 if x<0 else 4),y,-1)
    # Hood screws: M4 through holes, captive nuts accessed underneath the base.
    for x in [-58,58]:
        for y in [-55,55]:
            base+=cyl(5.5,35,x,y)
            base-=cyl(2.2,40,x,y,-1)
            base-=M.cylinder(3.6,4.2,circular_segments=6).translate((x,y,-.1))
    pc=P['pipe_center_x_mm']; pr=(P['pipe_od_mm']+P['pipe_diametral_clearance_mm'])/2
    for x in [pc-29,pc+29]:
        for y in [-30,30]: base-=cyl(2.2,7,x,y,-1)
    hood=box(w+8,d+8,31,cz=20)-box(w+2,d+2,34,cz=19)
    outer=m.CrossSection.square((w+8,d+8),center=True).extrude(10,scale_top=((w-14)/(w+8),(d-14)/(d+8))).translate((0,0,50))
    inner=m.CrossSection.square((w+2,d+2),center=True).extrude(8,scale_top=((w-20)/(w+2),(d-20)/(d+2))).translate((0,0,49))
    hood+=outer-inner
    for x in [-58,58]:
        for y in [-55,55]:
            hood+=cyl(5.5,22,x,y,35)
            hood-=cyl(2.2,35,x,y,30)
    # Split collar and flange, 40 mm engagement. Two M5 transverse clamp bolts.
    collar=cyl(pr+7,40,pc,0,-40)-cyl(pr,47,pc,0,-41)
    collar+=box(78,80,5,pc,0,-5)-cyl(pr,8,pc,0,-6)
    for x in [pc-31,pc+31]:
        collar+=box(14,24,24,x,0,-33)
        collar-=hole_y(2.75,40,x,20,-21)
        nut=M.cylinder(5,4.75,circular_segments=6).rotate((90,0,0)).translate((x,12.1,-21))
        collar-=nut
    for x in [pc-29,pc+29]:
        for y in [-30,30]: collar-=cyl(2.2,9,x,y,-7)
    front=collar ^ box(180,100,60,0,50.4,-50)
    back=collar ^ box(180,100,60,0,-50.4,-50)
    coupon=cyl(pr+4,8)-cyl(pr,10,z=-1)
    return {'base':base,'rain_hood':hood,'connector_rain_well':well,'pipe_clamp_front':front,'pipe_clamp_back':back,'pipe_fit_coupon':coupon}

def main():
    out=ROOT/'stl'; out.mkdir(exist_ok=True)
    stats={}
    for name,solid in parts().items():
        assert solid.status()==m.Error.NoError,(name,solid.status())
        mesh=solid.to_mesh()
        t=trimesh.Trimesh(vertices=np.array(mesh.vert_properties)[:,:3],faces=np.array(mesh.tri_verts),process=True)
        assert t.is_watertight and t.is_volume,name
        assert len(t.split())==1,(name,'disconnected solids')
        # Export in the design coordinate system; assembly remains reproducible.
        t.export(out/f'{name}.stl')
        stats[name]={'watertight':True,'connected_solids':1,'volume_cm3':round(t.volume/1000,2),'bounds_mm':t.bounds.tolist(),'triangles':len(t.faces)}
    (ROOT/'mesh_checks.json').write_text(json.dumps(stats,indent=2)+'\n')
    print(json.dumps(stats,indent=2))

if __name__=='__main__': main()
