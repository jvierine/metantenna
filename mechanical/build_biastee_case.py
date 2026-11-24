"""Indoor bias-tee case, dimensions in mm; side-entry Amphenol 132203 jacks.

Connector envelope follows 132203 drawing: axis 6.35 above PCB top,
16.50 from pin centre to mating tip, 8 mm body width, <=2.4 mm panel.
Print a fit sample before committing to a batch. No IP rating is claimed.
"""
from pathlib import Path
import json
import numpy as np
import trimesh
import manifold3d as m
from build_enclosure import box,cyl
R=Path(__file__).resolve().parents[1]
M=m.Manifold
PCB_Z=7.0
AXIS_Z=PCB_Z+1.6+6.35
# 2 mm sidewalls. Open-top U-slots admit the soldered connector barrels.
# Lid tongues close the slots after the populated PCB has been lowered in.
X0,X1=-3.0,79.0
Y0,Y1=-3.0,67.0

def horizontal_hole(radius,length,x,y,z):
    return M.cylinder(length,radius,circular_segments=64).rotate((0,90,0)).translate((x,y,z))

def parts():
    base=box(X1-X0,Y1-Y0,24,38,32)-box(78,66,26,38,32,3)
    board=json.loads((R/'vhf/hardware/biastee_layout.json').read_text())
    for p in board['parts']:
        if p['package']=='SMA_RA':
            assert p['mpn']=='132203'
            base-=horizontal_hole(3.4,100,-10,p['y'],AXIS_Z)
            base-=box(100,7.2,30,38,p['y'],AXIS_Z)
    # M3 PCB screws; 4 mm underside clearance for the 3.94 mm pins.
    for x in [6,70]:
        for y in [6,58]:
            base+=cyl(3.3,PCB_Z,x,y)
            base-=cyl(1.3,PCB_Z+1,x,y,3)
    # Lid fasteners use separate side bosses, outside the PCB rectangle.
    for x in [-5,81]:
        for y in [3,61]:
            base+=cyl(3,24,x,y)
            base-=cyl(1.25,22,x,y,4)
    # Rear 12 V cable opening. Fit a grommet and secure the cable internally.
    base-=M.cylinder(10,3.2,circular_segments=48).rotate((90,0,0)).translate((40,2,12))
    lid=box(94,70,2.5,38,32,24)
    # Captive tongues form the upper halves of the side openings. Leave 0.2 mm
    # clearance per side so the lid slides in without forcing the printed base.
    for x in [-2,78]:
        for y in [27,50]:
            tongue=box(1.6,6.8,24-AXIS_Z,x,y,AXIS_Z)
            tongue-=horizontal_hole(3.4,100,-10,y,AXIS_Z)
            lid+=tongue
    for x in [-5,81]:
        for y in [3,61]:lid-=cyl(1.7,5,x,y,23)
    return {'biastee_base':base,'biastee_lid':lid}

def mesh(s):
    q=s.to_mesh()
    return trimesh.Trimesh(np.asarray(q.vert_properties)[:,:3],np.asarray(q.tri_verts),process=True)

def main():
    solids=parts()
    # Check the PCB solid against the case and the washer envelope against lid/floor.
    pcb=box(76,64,1.6,38,32,PCB_Z)
    assert (solids['biastee_base'] ^ pcb).volume()<1e-6
    assert AXIS_Z-5.1>3 and AXIS_Z+5.1<24
    # Check the complete insertion sweep, not just the final resting position.
    # Nuts/washers are fitted externally AFTER insertion; no cable is attached.
    sweep=box(76,64,41.6,38,32,PCB_Z)
    board=json.loads((R/'vhf/hardware/biastee_layout.json').read_text())
    for p in board['parts']:
        if p['package']=='SMA_RA':
            direction=-1 if p['rotation']==0 else 1
            x,y=p['x'],p['y']
            sweep+=box(8,8,50.44,x,y,PCB_Z+1.6)
            start=x-16.5 if direction<0 else x+4
            sweep+=horizontal_hole(3.175,12.5,start,y,AXIS_Z)
            sweep+=box(12.5,6.35,40,start+6.25,y,AXIS_Z)
        else:
            w,d,h=(10,8,10) if p['package']=='TERM2' else (7,6,3.5) if p['package']=='ACM7060' else (4.7,4.5,2) if p['package']=='ACM4520' else (3,2,1.5)
            sweep+=box(w,d,h+40,p['x'],p['y'],PCB_Z+1.6)
    interference=(sweep ^ solids['biastee_base']).volume()
    assert interference<1e-6,('assembled-board insertion blocked',interference)
    assert (solids['biastee_lid'] ^ solids['biastee_base']).volume()<1e-6
    stats={'assembly_check':{'vertical_insertion_sweep_mm':40,
                            'interference_mm3':interference,
                            'sequence':'Remove nuts; lower populated PCB into U-slots; screw PCB down; fit lid; fit external washers and nuts.'}}
    for name,s in solids.items():
        t=mesh(s)
        assert s.status()==m.Error.NoError and t.is_watertight and t.is_volume
        assert len(t.split())==1,name
        t.export(R/'mechanical/stl'/f'{name}.stl')
        stats[name]={'watertight':True,'connected_solids':1,'bounds_mm':t.bounds.tolist(),'volume_cm3':round(t.volume/1000,2)}
    (R/'mechanical/biastee_mesh_checks.json').write_text(json.dumps(stats,indent=2)+'\n')
    render()

def render():
    import pyvista as pv
    from PIL import Image,ImageDraw
    for exploded in [False,True]:
        solids=parts()
        if exploded:solids['biastee_lid']=solids['biastee_lid'].translate((0,0,27))
        else:solids.pop('biastee_lid') # Open top makes the side-entry geometry visible.
        solids['pcb']=box(76,64,1.6,38,32,PCB_Z)
        a=json.loads((R/'vhf/hardware/biastee_layout.json').read_text())
        for p in a['parts']:
            if p['package']=='SMA_RA':
                direction=-1 if p['rotation']==0 else 1
                x,y=p['x'],p['y']
                body=box(8,8,10.44,x,y,PCB_Z+1.6)
                barrel=horizontal_hole(3.175,12.5,x+direction*4 if direction>0 else x-16.5,y,AXIS_Z)
                barrel-=horizontal_hole(2.05,18,x-18 if direction<0 else x+3,y,AXIS_Z)
                solids[p['ref']]=body+barrel
                nut=horizontal_hole(4.6,1.6,-4.6 if direction<0 else 79,y,AXIS_Z)-horizontal_hole(3.2,3,-5 if direction<0 else 78.5,y,AXIS_Z)
                solids[p['ref']+'_nut']=nut
            else:
                w,d,h=(10,8,10) if p['package']=='TERM2' else (7,6,3.5) if p['package']=='ACM7060' else (4.7,4.5,2) if p['package']=='ACM4520' else (3,2,1.5)
                solids[p['ref']]=box(w,d,h,p['x'],p['y'],PCB_Z+1.6)
        plot=pv.Plotter(off_screen=True,window_size=(1400,1000));plot.set_background('white')
        for name,s in solids.items():
            t=mesh(s);faces=np.column_stack([np.full(len(t.faces),3),t.faces]).ravel()
            color='#d4dce1' if name.startswith('biastee') else '#246c49' if name=='pcb' else '#c8a24b' if name.startswith('J') else '#343a3d'
            plot.add_mesh(pv.PolyData(t.vertices,faces),color=color,ambient=.4,diffuse=.6)
        plot.camera_position=[(-125,155,160),(38,32,13),(0,0,1)]
        plot.enable_parallel_projection();plot.reset_camera();plot.camera.zoom(1.12)
        path=R/'vhf/docs'/('biastee_case_exploded.png' if exploded else 'biastee_case_open.png')
        plot.screenshot(str(path));plot.close()
        im=Image.open(path);dr=ImageDraw.Draw(im)
        dr.text((25,20),'Bias tee: horizontal side-entry SMA connectors',fill='black',font_size=28)
        dr.text((25,65),'Left: X antenna + 12 V / Y antenna     Right: X / Y receiver',fill='black',font_size=22)
        im.save(path)
if __name__=='__main__':main()
