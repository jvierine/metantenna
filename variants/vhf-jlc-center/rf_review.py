"""Screen RF route geometry and nominal 50-ohm cross-sections."""
from pathlib import Path
import json

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from shapely.geometry import LineString, Point

HERE = Path(__file__).resolve().parent


def capacitance(width, height, dk, gap, step=.008):
    # 2D quasi-static solve with an adjacent ground plane, 40 um copper
    # and 20 um conformal solder mask. Units in the mesh are millimetres.
    x = np.arange(-2, 2+step/2, step)
    y = np.arange(-height, .9+step/2, step)
    xx, yy = np.meshgrid(x, y, indexing='ij')
    copper = (yy >= -1e-8) & (yy <= .04+1e-8)
    driven = copper & (abs(xx) <= width/2)
    fixed = driven.copy()
    fixed[:,0] = fixed[:,-1] = fixed[0,:] = fixed[-1,:] = True
    if gap is not None:
        fixed |= copper & (abs(xx) >= width/2 + gap)
    er = np.ones_like(xx)
    er[yy < -1e-8] = dk
    if dk > 1:
        er[(yy >= -1e-8) & (yy < .02)] = 3.3
        er[(abs(xx) < width/2+.02) & (yy >= 0) & (yy < .06)] = 3.3
    index = np.full(xx.shape, -1)
    index[~fixed] = np.arange((~fixed).sum())
    u,v = np.where(~fixed)
    row=[]; col=[]; val=[]
    rhs=np.zeros(len(u)); diagonal=np.zeros(len(u))
    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
        a,b=u+dx,v+dy
        e=2*er[u,v]*er[a,b]/(er[u,v]+er[a,b])
        unknown=~fixed[a,b]
        row.extend(index[u[unknown],v[unknown]])
        col.extend(index[a[unknown],b[unknown]])
        val.extend(-e[unknown])
        rhs+=e*driven[a,b]
        diagonal+=e
    row.extend(range(len(u)));col.extend(range(len(u)));val.extend(diagonal)
    volt=driven.astype(float)
    volt[u,v]=spsolve(coo_matrix((val,(row,col)),shape=(len(u),len(u))).tocsr(),rhs)
    charge=0.
    u,v=np.where(driven)
    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
        a,b=u+dx,v+dy
        charge+=np.sum(er[a,b]*(1-volt[a,b]))
    return charge


def impedance(width, height, dk, gap):
    c=capacitance(width,height,dk,gap)
    c0=capacitance(width,height,1,gap)
    return float(376.730313668 / np.sqrt(c*c0))


def geometry():
    d=json.loads((HERE/'hardware/preamp_layout.json').read_text())
    traces=[(n,l,LineString([a,b]).buffer(w/2)) for n,l,a,b,w in d['tracks']]
    report={}
    for net in ('X_COAX','Y_COAX'):
        distances=[]
        for n,l,g in traces:
            if n!=net:
                continue
            for other,ll,shape in traces:
                if ll==l and other.startswith(('X_ANT_','Y_ANT_','X_RF_IN','Y_RF_IN','X_AMP_IN','Y_AMP_IN')):
                    distances.append((g.distance(shape),other))
        gap,aggressor=min(distances)
        signal_vias=[(x,y) for n,x,y in d['vias'] if n==net]
        grounds=[Point(x,y) for n,x,y in d['vias'] if n=='GND']
        report[net]={
            'trace_width_mm':sorted({w for n,l,a,b,w in d['tracks'] if n==net}),
            'minimum_same_layer_gap_to_input_trace_mm':round(gap,3),
            'nearest_input_net':aggressor,
            'nearest_ground_via_mm':[
                round(min(Point(x,y).distance(g) for g in grounds),3) for x,y in signal_vias
            ],
        }
    return report


if __name__=='__main__':
    results={
        'geometry':geometry(),
        'impedance_ohm':{
            'outer_dielectric_0p2104mm_ground_fill_0p5mm':impedance(.34,.2104,4.2,.5),
            'outer_dielectric_0p2104mm_without_side_fill':impedance(.34,.2104,4.2,None),
            'outer_dielectric_0p1164mm_ground_fill_0p5mm':impedance(.34,.1164,4.2,.5),
        },
        'trace_model_width_mm':.34,
        'biastee_uniform_0p32mm_ohm':impedance(.32,.2104,4.2,.5),
        'scope':'2D uniform line only. Dk assumed 4.2; excludes via and SMA 3D launches, component pads, and coupling.',
    }
    (HERE/'simulation/rf_review.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))
