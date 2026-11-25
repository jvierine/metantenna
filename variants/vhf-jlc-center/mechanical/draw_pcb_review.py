"""Draw the KiCad copper layers and a package-envelope assembly view."""
from pathlib import Path
import io
import json
import re
import shutil
import subprocess
import tempfile

import cairosvg
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
VARIANT = HERE.parent
KICAD = shutil.which('kicad-cli') or '/Volumes/KiCad/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
LAYER_VIEWS = {
    'F.Cu': 'L1 · Front signals and ground fill',
    'In1.Cu': 'L2 · Ground reference',
    'In2.Cu': 'L3 · Ground reference',
    'B.Cu': 'L4 · Back signals and ground fill',
}
BODIES = {
    '0805': (2,1.25,.65), '1206': (3.2,1.6,.9), '2512': (6.4,3.2,.65),
    'APV2012': (2,1.78,1.45), 'APV2520': (2.9,2.8,2),
    'SMA_DIODE': (4.3,2.6,2), 'SOT89': (4.5,3.2,1.5),
    'MSOP8EP': (3,3,1.1), 'CD542': (5.6,7.9,3),
    'ACM4520': (4.7,4.5,2), 'ACM7060': (7,6,3.5),
    'TERM2': (10.2,8.5,10), 'SMA_RA': (6,6,10),
}


def layer_image(name, layers, temporary, *, appearance=None):
    source = VARIANT / 'validation' / name / 'source' / f'{name}.kicad_pcb'
    dest = temporary / (name + layers.replace(',', '-') + '.svg')
    subprocess.run([KICAD, 'pcb', 'export', 'svg', '--exclude-drawing-sheet', '-l', layers, '-o', str(dest), str(source)],
                   check=True, capture_output=True)
    w,h = (96,96) if name=='preamp' else (76,64)
    svg = re.sub(r'width="[^"]+" height="[^"]+" viewBox="[^"]+"',
                 f'width="{w+2}mm" height="{h+2}mm" viewBox="-1 -1 {w+2} {h+2}"',
                 dest.read_text(), count=1)
    if appearance == 'copper':
        svg = svg.replace('#C83434','#31584d').replace('#FFFFFF','#a1b6ab')
    elif appearance == 'silk':
        svg = svg.replace('#F2EDA1','#ffffff').replace('#C872AB','#ffffff')
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(),
                                                  background_color=None if appearance=='silk' else 'white', output_width=1300)))


def draw_layers(name, temporary):
    fig,axs=plt.subplots(2,2,figsize=(10,10),layout='constrained')
    for ax,(layer,title) in zip(axs.flat,LAYER_VIEWS.items()):
        ax.imshow(layer_image(name,layer+',Edge.Cuts',temporary))
        ax.set_title(title,loc='left',fontsize=12)
        ax.axis('off')
    fig.savefig(HERE/f'{name}_copper_layers.png',dpi=155)
    plt.close(fig)
    front = layer_image(name,'F.Cu,Edge.Cuts',temporary,appearance='copper').convert('RGBA')
    silk = layer_image(name,'F.SilkS',temporary,appearance='silk').convert('RGBA')
    front = Image.alpha_composite(front,silk)
    front.save(HERE/f'{name}_front_silkscreen.png')
    if name == 'preamp':
        front.save(HERE/'center_sma_pcb.png')


def draw_assembly(name):
    layout=json.loads((VARIANT/'hardware'/f'{name}_layout.json').read_text())
    fig=plt.figure(figsize=(10,8),layout='constrained')
    ax=fig.add_subplot(projection='3d')
    w,h=layout['size_mm']
    ax.bar3d(0,0,0,w,h,1.6,color='#6f9d8e',alpha=.28,shade=True)
    for p in layout['parts']:
        if p['value'].startswith('DNP') or p['package']=='ANT_M3':
            continue
        x,y=p['x'],h-p['y']
        if p['package']=='SMA':
            a=np.linspace(0,2*np.pi,28)
            t,z=np.meshgrid(a,[1.6,11.1])
            ax.plot_surface(x+3.25*np.cos(t),y+3.25*np.sin(t),z,color='#b28a38',linewidth=0)
            ax.plot_trisurf(x+3.25*np.cos(a[:-1]),y+3.25*np.sin(a[:-1]),np.full(len(a)-1,11.1),color='#d4b86c')
        elif p['package']=='SMA_RA':
            side=-1 if x<w/2 else 1
            a=np.linspace(0,2*np.pi,28)
            t,u=np.meshgrid(a,[x,x+side*20])
            ax.bar3d(x-3,y-3,1.6,6,6,7,color='#a17a32',shade=True)
            ax.plot_surface(u,y+3.1*np.cos(t),8.1+3.1*np.sin(t),color='#b28a38',linewidth=0)
        else:
            dx,dy,dz=BODIES[p['package']]
            if p['rotation']%180:dx,dy=dy,dx
            color='#a17a32' if p['ref'].startswith('J') else '#343b44'
            ax.bar3d(x-dx/2,y-dy/2,1.6,dx,dy,dz,color=color,shade=True)
        if p['ref'].startswith(('J','T','U','CM')):
            offset = -4 if p['package']=='SMA' else 0
            ax.text(x,y+offset,15,p['ref'],fontsize=7,ha='center',color='#183138')
    margin=17 if name=='biastee' else 0
    ax.set(xlim=(-margin,w+margin),ylim=(0,h),zlim=(0,20))
    ax.set_box_aspect((w,h,18))
    ax.view_init(elev=54,azim=-111)
    ax.set_axis_off()
    fig.savefig(HERE/f'{name}_3d_placement.png',dpi=180)
    plt.close(fig)


if __name__=='__main__':
    with tempfile.TemporaryDirectory() as td:
        for name in ('preamp','biastee'):
            draw_layers(name,Path(td))
            draw_assembly(name)
