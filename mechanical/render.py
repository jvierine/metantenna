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
        solids['connector_rain_well']=solids['connector_rain_well'].translate((45,0,-15))
        solids['pipe_clamp_front']=solids['pipe_clamp_front'].translate((0,18,-15))
        solids['pipe_clamp_back']=solids['pipe_clamp_back'].translate((0,-18,-15))
    solids['pipe']=cyl(25,90,-23,0,-130)-cyl(22,92,-23,0,-131)
    z=67 if exploded else 15
    pcb=box(96,96,1.6,cz=z)
    for x in [-42,42]:
        for y in [-42,42]:pcb-=cyl(1.6,4,x,y,z-1)
    solids['pcb']=pcb
    for i,y in enumerate([-22,18]):solids['sma'+str(i)]=cyl(3.2,9.53,42,y,z-9.53)
    colors={'base':(206,214,220),'rain_hood':(234,237,240),'connector_rain_well':(192,203,213),'pipe_clamp_front':(195,207,217),'pipe_clamp_back':(195,207,217),'pipe':(173,180,186),'pcb':(48,107,71),'sma0':(192,159,73),'sma1':(192,159,73)}
    eye=np.array([1.,-1.5,.85]);eye/=np.linalg.norm(eye)
    right=np.cross([0,0,1],eye);right/=np.linalg.norm(right);up=np.cross(eye,right)
    basis=np.array([right,-up,eye]).T
    records=[];allxy=[]
    for name,s in solids.items():
        t=mesh(s);v=np.asarray(t.vertices)@basis;allxy.extend(v[:,:2])
        for face,normal in zip(t.faces,t.face_normals):
            if np.dot(normal,eye)<-.01:continue
            shade=.50+.50*max(0,np.dot(normal,np.array([.3,-.5,.812])))
            color=tuple(int(c*shade) for c in colors[name])
            records.append((v[face,2].mean(),v[face,:2],color))
    a=np.array(allxy);low=a.min(axis=0);high=a.max(axis=0)
    size=np.array([1200,1400]);scale=min((size-100)/(high-low))
    im=Image.new('RGB',tuple(size*2),'white');d=ImageDraw.Draw(im)
    for _,xy,color in sorted(records,key=lambda a:a[0]):
        px=(xy-low)*scale+50;d.polygon([tuple(p*2) for p in px],fill=color)
    im.resize(tuple(size),Image.Resampling.LANCZOS).save(R/'docs'/('enclosure_exploded.png' if exploded else 'enclosure_assembled.png'))

if __name__=='__main__':render(False);render(True)
