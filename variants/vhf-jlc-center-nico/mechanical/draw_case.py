"""Draw the centered PCB connectors and straight cable passage."""
from pathlib import Path

import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
layout = json.loads((HERE.parent/'hardware'/'preamp_layout.json').read_text())
jacks = {p['ref']: (p['x']-48,48-p['y']) for p in layout['parts'] if p['ref'] in ('J102','J202')}
plug_radius = 6
bore_radius = 18
assert all(np.hypot(x,y)+plug_radius < bore_radius for x,y in jacks.values())
assert np.linalg.norm(np.subtract(jacks['J102'],jacks['J202'])) > 2*plug_radius
assert max(x for x,y in jacks.values())+3 < 17-2.75

fig = plt.figure(figsize=(7, 5), layout='constrained')
ax = fig.add_subplot(projection='3d')
for name, color, alpha in [('base','#536879',.055),('rain_hood','#8596a3',.06)]:
    mesh = trimesh.load_mesh(HERE/'stl'/f'{name}.stl')
    ax.add_collection3d(Poly3DCollection(mesh.triangles,facecolor=color,edgecolor='none',alpha=alpha))
pcb = [(-48,-48,15),(48,-48,15),(48,48,15),(-48,48,15)]
ax.add_collection3d(Poly3DCollection([pcb],facecolor='#36664b',alpha=.65))
for ref, label, color in [('J102','X RF + 12 V','#b24b1f'),('J202','Y RF','#21619a')]:
    x,y=jacks[ref]
    ax.plot([x,x],[y,y],[5.5,15],color='#a47723',linewidth=7)
    ax.plot([x,x],[y,y],[-58,5.5],color=color,linewidth=4,label=label)
ax.plot([0,0],[0,0],[-58,0],linestyle='--',color='#46505a',linewidth=1)
ax.set(xlim=(-83,83),ylim=(-80,80),zlim=(-60,62))
ax.set_box_aspect((166,160,122))
ax.view_init(elev=18,azim=-57)
ax.set_axis_off()
ax.legend(loc='upper left',frameon=False)
fig.savefig(HERE/'center_sma_cable_entry.png',dpi=180)
