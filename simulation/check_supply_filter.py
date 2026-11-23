"""Topology and SPICE screening of the installed differential supply filter.

Ferrite and choke RF models below are explicit screening approximations, not
vendor-fitted S parameters. No measured common-mode attenuation is inferred.
"""
from pathlib import Path
import sys,json,tempfile,subprocess
import numpy as np
import h5py
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'hardware'))
from design import biastee
p={x.ref:x for x in biastee()[0]}
assert p['CM1'].nets=={'1':'VIN_FUSED','2':'SUPPLY_RETURN','3':'GND','4':'CM_POS'}
assert [(x.ref,k) for x in p.values() for k,n in x.nets.items() if n=='SUPPLY_RETURN']==[('J1','2'),('CM1','2')]
assert p['FB1'].nets=={'1':'PROTECTED','2':'FILTERED'}
assert p['F10'].nets['1']=='FILTERED'
# Verify input return stays inside the copper-free island on either routing layer.
a=json.loads((R/'hardware/biastee_layout.json').read_text())
for n,layer,start,end,width in a['tracks']:
 if n=='SUPPLY_RETURN':
  assert all(34+width/2<x<50-width/2 and .5+width/2<y<14-width/2 for x,y in [start,end])
reports=[];curves=[]
for source_r in [.1,1,50]:
 for scale in [.3,1,3]:
  deck=f'''Differential supply filter screening
V1 src 0 DC 12 AC 1
Rs src a {source_r}
Rcm a cm .03
Lleak cm b {scale*.1}u
* Bead: screening RL-parallel-loss model, with parasitic C.
Rdc b d .14
Lfb d e {scale*.9}u
Rloss d e 600
Cfb d e .2p
* C1 upstream of bead, bypass stack downstream.
Rpre b b1 .05
Lpre b1 b2 1n
Cpre b2 0 3u
R2 e c2 .03
L2 c2 c2a .5n
C2 c2a 0 1n
R3 e c3 .03
L3 c3 c3a .8n
C3 c3a 0 100n
Rdamp e c4 1
L4 c4 c4a 1n
C4 c4a 0 3u
* Existing PTC/local bypass and bias injection branch.
Rft e local .5
Rlocal local cl .03
Llocal cl cl2 .8n
Clocal cl2 0 100n
Rbias local lb 1.8
Lbias lb coax 1u
Cpar lb coax .5p
Rrx coax 0 50
.control
set wr_singlescale
set wr_vecnames
ac dec 60 1k 150meg
let transfer=v(coax)
let rail=v(e)
wrdata response.txt transfer rail
quit
.endc
.end
'''
  with tempfile.TemporaryDirectory() as td:
   q=Path(td);(q/'filter.cir').write_text(deck)
   subprocess.run(['ngspice','-b','filter.cir'],cwd=q,capture_output=True,check=True)
   z=np.loadtxt(q/'response.txt',skiprows=1)
  f=z[:,0];coax=20*np.log10(abs(z[:,1]+1j*z[:,2]));rail=20*np.log10(abs(z[:,3]+1j*z[:,4]))
  assert np.isfinite(coax).all() and rail.max()<3,('resonance',source_r,scale,rail.max())
  curves.append((coax,rail))
  reports.append({'source_ohm':source_r,'inductance_scale':scale,'rail_peak_dB':float(rail.max()),'coax_transfer_30_55_dB_max':float(coax[(f>=30e6)&(f<=55e6)].max())})
with h5py.File(R/'simulation/supply_filter.h5','w') as h:
 h['frequency_Hz']=f;h['coax_transfer_dB']=np.array([c[0] for c in curves]);h['filtered_rail_transfer_dB']=np.array([c[1] for c in curves])
 h.attrs['model_limit']='Differential screening only; approximate ferrite/choke RF model, 50ohm coax load, 0.1/1/50ohm supply impedance. Not a common-mode or measured-EMC result.'
 h.attrs['cases']=json.dumps(reports)
summary={'topology':'pass','input_return_copper_island':'pass','cases':reports,'DC_drop_at_0p191A_V_max_20C':.17*.191,'added_dissipation_W_max_20C':.17*.191**2,'common_mode_suppression':'Requires bench measurement; no quantitative claim from this model.'}
(R/'simulation/supply_filter_results.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
