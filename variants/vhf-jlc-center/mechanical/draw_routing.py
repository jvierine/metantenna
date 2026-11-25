"""Draw native board routing in the Calinject review style."""
from pathlib import Path
import math

import matplotlib.pyplot as plt
from matplotlib import patheffects
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle, Ellipse, Polygon, Rectangle
import sexpdata

HERE = Path(__file__).resolve().parent
PALE, DARK, GOLD = '#f2f7f5', '#203b34', '#d7b052'
FRONT, BACK = '#ba2838', '#3069b2'


def items(node, name):
    return [x for x in node if isinstance(x,list) and x and str(x[0])==name]


def fld(node, name):
    return items(node,name)[0][1:]


def render(name):
    board = sexpdata.loads((HERE.parent/'hardware'/f'{name}.kicad_pcb').read_text())
    w,h = (96,96) if name=='preamp' else (76,64)
    fig,ax=plt.subplots(figsize=(13,13*h/w),layout='constrained')
    ax.set(xlim=(-18,w+18) if name=='biastee' else (-2,w+2),ylim=(h+4,-2))
    ax.set_aspect('equal')
    ax.axis('off')
    ax.add_patch(Rectangle((0,0),w,h,facecolor=PALE,edgecolor=DARK,linewidth=1.4))
    for layer,color,z in [('B.Cu',BACK,2),('F.Cu',FRONT,3)]:
        traces=[t for t in items(board,'segment') if fld(t,'layer')[0]==layer]
        ax.add_collection(LineCollection(
            [[fld(t,'start'),fld(t,'end')] for t in traces], colors=color,
            linewidths=[fld(t,'width')[0]*8 for t in traces],zorder=z,
            capstyle='round',joinstyle='round'))
    for via in items(board,'via'):
        x,y=fld(via,'at')[:2]
        for key,color,z in [('size',GOLD,4),('drill',PALE,5)]:
            ax.add_patch(Circle((x,y),fld(via,key)[0]/2,facecolor=color,edgecolor='none',zorder=z))
    labels=[]
    for fp in items(board,'footprint'):
        x,y,*rot=fld(fp,'at')
        theta=math.radians(rot[0] if rot else 0)
        def global_xy(u,v):
            return x+math.cos(theta)*u+math.sin(theta)*v,y-math.sin(theta)*u+math.cos(theta)*v
        if fp[1].endswith(':SMA_RA'):
            side=-1 if x<w/2 else 1
            ax.add_patch(Rectangle((min(x+side*3,x+side*20),y-3),17,6,
                                   facecolor='#e5cc8a',edgecolor='#b18c32',zorder=4))
        for p in items(fp,'pad'):
            u,v,*pr=fld(p,'at')
            center=global_xy(u,v)
            dx,dy=fld(p,'size')
            if str(p[2])=='np_thru_hole':
                ax.add_patch(Ellipse(center,dx,dy,facecolor='white',edgecolor=DARK,linewidth=.8,zorder=6))
                continue
            if str(p[3])=='circle':
                patch=Ellipse(center,dx,dy,facecolor=GOLD,edgecolor='none',zorder=6)
            else:
                patch=Rectangle((center[0]-dx/2,center[1]-dy/2),dx,dy,
                    angle=-(pr[0] if pr else 0),rotation_point='center',facecolor=GOLD,edgecolor='none',zorder=6)
            ax.add_patch(patch)
            if items(p,'drill'):
                drill=fld(p,'drill')[0]
                ax.add_patch(Circle(center,drill/2,facecolor=PALE,edgecolor='none',zorder=7))
        for t in items(fp,'fp_text'):
            if fld(t,'layer')[0]=='F.SilkS':
                labels.append((t[2],*global_xy(*fld(t,'at')[:2]),False))
    for t in items(board,'gr_text'):
        x,y=fld(t,'at')[:2]
        if fld(t,'layer')[0]=='F.SilkS':
            labels.append((t[1],x,y,' ' in t[1] or t[1] in ('-','X+','X-','Y+','Y-')))
    for poly in items(board,'gr_poly'):
        if fld(poly,'layer')[0]=='F.SilkS':
            ax.add_patch(Polygon([p[1:3] for p in fld(poly,'pts')],facecolor=DARK,edgecolor='none',zorder=8))
    for label,x,y,bold in labels:
        ax.text(x,y,label,ha='center',va='center',zorder=9,color=DARK,
                fontsize=9.5 if bold else 8.2,weight='bold' if bold else 'normal',
                path_effects=[patheffects.withStroke(linewidth=2.4,foreground=PALE)])
    ax.text(w/2,h+2.7,'Top view  ·  red: front copper  ·  blue: back copper  ·  gold: pads and vias',
            color=DARK,fontsize=10,ha='center',va='center')
    fig.savefig(HERE/f'{name}_routing.png',dpi=180)
    plt.close(fig)


if __name__=='__main__':
    for name in ('preamp','biastee'):
        render(name)
