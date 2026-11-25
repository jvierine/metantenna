"""Draw the installed cable paths over the enclosure CAD meshes."""
from pathlib import Path
import sys

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from scipy.spatial import ConvexHull
import trimesh

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'mechanical'))
import build_enclosure as enclosure

CABLE_RADIUS = 3.0
MATING_RADIUS = 6.0
PIPE_BORE = 36.0
BEND_START = -16.0
PIPE_ENTRY = enclosure.CABLE_ENTRY_Z
BOLT_X = enclosure.SOCKET_BOLT_OFFSET_X
SOCKET_CENTER = np.array([enclosure.CABLE_SOCKET_X, enclosure.CABLE_SOCKET_Y])


def cable_path(start, end):
    """Two tangent circular arcs between parallel vertical cable segments."""
    offset = end - start
    d = np.linalg.norm(offset)
    h = BEND_START - PIPE_ENTRY
    r = (h*h + d*d)/(4*d)
    angle = 2*np.arctan2(d, h)
    t = np.linspace(0, angle, 100)
    lateral = r*(1-np.cos(t))
    drop = r*np.sin(t)
    lateral = np.r_[lateral, d-lateral[-2::-1]]
    drop = np.r_[drop, h-drop[-2::-1]]
    xy = start + lateral[:, None]*offset/d
    return np.column_stack((xy, BEND_START-drop)), r


def check_paths():
    _, inner = enclosure.cable_chamber()
    # Exclude end planes where the path continues into an open adjoining bore.
    planes = ConvexHull(inner.to_mesh().vert_properties[:, :3]).equations
    sides = planes[np.abs(planes[:, 2]) < 0.999]
    paths = []
    for (x, y), pipe_y in zip(enclosure.P['sma_centers_mm'], (7., -7.)):
        start = np.array([x, -y])
        end = SOCKET_CENTER + [0., pipe_y]
        curve, radius = cable_path(start, end)
        plug = np.column_stack((np.tile(start, (2, 1)), [5.5, BEND_START]))
        assert np.max(plug @ sides[:, :3].T + sides[:, 3]) < -MATING_RADIUS
        assert np.max(curve @ sides[:, :3].T + sides[:, 3]) < -CABLE_RADIUS
        assert np.linalg.norm(end - SOCKET_CENTER) + MATING_RADIUS < PIPE_BORE / 2
        assert BOLT_X - 2.75 > CABLE_RADIUS
        full = np.vstack((plug, curve[1:], [*end, -104]))
        paths.append((full, radius))
    # Both paths share a common vertical parameter, so compare at equal heights.
    z = np.linspace(-104, 5.5, 300)
    a, b = (np.column_stack([np.interp(z, p[::-1, 2], p[::-1, k])
                             for k in (0, 1)]) for p, _ in paths)
    assert np.min(np.linalg.norm(a-b, axis=1)) > 2*MATING_RADIUS
    return paths


def draw(paths):
    fig = plt.figure(figsize=(8, 8), layout='constrained')
    ax = fig.add_subplot(projection='3d')
    for name, color, alpha, step in [
        ('base', '#536879', .065, 3), ('rain_hood', '#8596a3', .09, 2),
    ]:
        mesh = trimesh.load_mesh(HERE/'stl'/f'{name}.stl')
        ax.add_collection3d(Poly3DCollection(mesh.triangles[::step], facecolor=color,
                                             edgecolor='none', alpha=alpha))
    pcb = [(-48,-48,15), (48,-48,15), (48,48,15), (-48,48,15)]
    ax.add_collection3d(Poly3DCollection([pcb], facecolor='#36664b', alpha=.6))
    for (p, radius), label, color in zip(paths, ('X RF + 12 V', 'Y RF'), ('#b24b1f','#21619a')):
        x, y = p[0,:2]
        ax.plot([x,x],[y,y],[5.5,15], color='#a47723', linewidth=7)
        ax.plot(*p.T, color=color, linewidth=4, label=f'{label} · {radius:.0f} mm bend radius')
    ax.plot([SOCKET_CENTER[0]]*2,[SOCKET_CENTER[1]]*2,[-104,PIPE_ENTRY], linestyle='--', color='#46505a', linewidth=1)
    ax.set(xlim=(-83,83), ylim=(-80,80), zlim=(-106,60),
           xlabel='X (mm)', ylabel='Y (mm)', zlabel='Height (mm)')
    ax.set_box_aspect((166,160,166))
    ax.view_init(elev=17, azim=-63)
    ax.legend(loc='upper left', frameon=False)
    fig.savefig(HERE/'centered_cable_entry.png', dpi=180)


if __name__ == '__main__':
    paths = check_paths()
    draw(paths)
    print('Minimum nominal bend radii (mm):', [round(r,1) for _, r in paths])
