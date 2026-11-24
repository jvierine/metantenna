"""Render the actual STL solids with a small orthographic CAD renderer."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import trimesh
from build_enclosure import parts,box,cyl

R=Path(__file__).resolve().parents[1]
def mesh(s):
    a=s.to_mesh();return trimesh.Trimesh(np.asarray(a.vert_properties)[:,:3],np.asarray(a.tri_verts),process=False)
def render(exploded):
    solids=parts();solids.pop('pipe_fit_coupon')
    if exploded:
        solids['rain_hood']=solids['rain_hood'].translate((0,0,105))
    solids['pipe']=cyl(25,125,-23,0,-130)-cyl(22,127,-23,0,-131)
    z=67 if exploded else 15
    pcb=box(96,96,1.6,cz=z)
    for x in [-42,42]:
        for y in [-42,42]:pcb-=cyl(1.6,4,x,y,z-1)
    solids['pcb']=pcb
    # Dimensional illustration of straight underside PCB SMA jacks.
    # Thread ridges are schematic, not a manufacturing connector model.
    for i,y in enumerate([-22,18]):
        x=42;bottom=z-9.53
        body=box(7,7,1.5,x,y,z-1.5)+cyl(2.9,8.03,x,y,bottom)
        for zz in np.arange(bottom+.3,z-1.5,.706):body+=cyl(3.175,.22,x,y,float(zz))
        body-=cyl(2.1,3.1,x,y,bottom-.1)
        for dx in [-2.54,2.54]:
            for dy in [-2.54,2.54]:body+=box(1.02,1.02,3,x+dx,y+dy,z-.1)
        body+=cyl(.63,3,x,y,z-.1)
        solids['sma'+str(i)]=body
        solids['ptfe'+str(i)]=cyl(2.05,2,x,y,bottom+.5)-cyl(.48,2.2,x,y,bottom+.4)

    # Populate this drawing from the actual Rev B component placement.
    board=json.loads((R/'vhf/hardware/preamp_layout.json').read_text())
    for p in board['parts']:
        if p['package'] in ['ANT_M3','SMA']:continue
        name='part_'+p['ref']
        ww,dd=(5,5) if p['ref'].startswith(('T','U')) else (2.2,1.4)
        solids[name]=box(ww,dd,1.4,p['x']-48,p['y']-48,z+1.6)
    colors={'base':(206,214,220),'rain_hood':(234,237,240),'connector_rain_well':(192,203,213),'pipe_clamp_front':(195,207,217),'pipe_clamp_back':(195,207,217),'pipe':(173,180,186),'pcb':(48,107,71),'sma0':(192,159,73),'sma1':(192,159,73)}
    import pyvista as pv
    plotter=pv.Plotter(off_screen=True,window_size=(1400,1500))
    plotter.set_background('white')
    for name,solid in solids.items():
        t=mesh(solid)
        faces=np.column_stack([np.full(len(t.faces),3),t.faces]).ravel()
        plotter.add_mesh(pv.PolyData(t.vertices,faces),color=np.array(colors.get(name,(240,238,220) if name.startswith('ptfe') else (55,59,62)))/255,
                         smooth_shading=False,ambient=.35,diffuse=.65,specular=.15)
    plotter.camera_position=[(280,-420,260),(0,0,15 if exploded else -25),(0,0,1)]
    plotter.enable_parallel_projection()
    plotter.reset_camera()
    plotter.screenshot(str(R/'vhf/docs'/('enclosure_exploded.png' if exploded else 'enclosure_assembled.png')))
    plotter.close()
    if not exploded:
        plotter=pv.Plotter(off_screen=True,window_size=(1200,850));plotter.set_background('white')
        for name,solid in solids.items():
            if not (name=='pcb' or name.startswith(('sma','ptfe'))):continue
            t=mesh(solid);faces=np.column_stack([np.full(len(t.faces),3),t.faces]).ravel()
            plotter.add_mesh(pv.PolyData(t.vertices,faces),color=np.array(colors.get(name,(240,238,220)))/255,ambient=.35)
        plotter.camera_position=[(100,-90,-70),(42,-2,12),(0,0,1)]
        plotter.enable_parallel_projection();plotter.camera.parallel_scale=30
        plotter.screenshot(str(R/'vhf/docs/sma_underside_detail.png'));plotter.close()

if __name__=='__main__':render(False);render(True)
