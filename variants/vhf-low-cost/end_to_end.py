"""Run the existing full-chain linear model with this variant's passive SPICE network.
The active stage remains behavioral; no physical or nonlinear qualification implied.
"""
from pathlib import Path
import json,sys,hashlib
import numpy as np
O=Path(__file__).resolve().parent;BASE=O.parents[1]
# Reuse the owning model while redirecting every output to the candidate folder.
s=(BASE/'simulation/end_to_end.py').read_text()
s=s.replace('Path(__file__).resolve().parents[1]',repr(str(BASE)))
s=s.replace('R='+repr(str(BASE)), 'R=Path('+repr(str(BASE))+')')
# Keep all imported models at their existing source; write only this candidate's outputs.
s=s.replace("R/'simulation/end_to_end.h5'", "Path("+repr(str(O/'simulation/end_to_end.h5'))+")")
s=s.replace("R/'simulation/end_to_end_results.json'", "Path("+repr(str(O/'simulation/end_to_end_results.json'))+")")
start=s.index(" vals=np.array(");end=s.index(' w=2*np.pi*f*1e6',start)
s=s[:start]+''' # upgrade_screen uses actual passive nominal values, independent two-port excitations.
 f=F.copy();ss=run(((True,False,True),VALUES,[70,35,70]))
 s11,s21,s12,s22=ss[:,0,0],ss[:,1,0],ss[:,0,1],ss[:,1,1]
 keep=f<=150;f=f[keep];s11=s11[keep];s21=s21[keep];s12=s12[keep];s22=s22[keep]
''' +s[end:]
# This SPICE network already includes the 0.5 dB balun and C115 input DC block.
s=s.replace("balun@pre@series(cap(coupling_cap('C115')))@amp", 'pre@amp')
s=s.replace("[-20,25,60]",'[-50,25,30]')
s=s.replace('ambient -20..60C','ambient -50..30C extrapolation; components not qualified below -40C')
# The old stored sky system-noise arrays belong to the original hardware, not this chain.
s=s.replace("for key in ['system_X_K','system_Y_K','sky_X_K','sky_Y_K']", "for key in ['sky_X_K','sky_Y_K']")
s=s.replace(", 'system_X_noise_K_median':float(np.median(sky[name]['system_X_K'][j]))",'')
ns={'__file__':str(BASE/'simulation/end_to_end.py'),'__name__':'candidate_model'}
# Load only the tested passive-model definitions; skip its historical Monte Carlo run.
ps=(O/'spice_tolerance.py').read_text().split('rng=np.random.default_rng')[0]
ps=ps.replace("cp=[.1,.1,.1] if variant=='original' else [1e12/((2*np.pi*f*1e6)**2*l*1e-9) for f,l in zip([820,1250,1100],VALUES[IND])]", "cp=[.1 if flag else 1e12/((2*np.pi*f*1e6)**2*l*1e-9) for flag,f,l in zip(variant,[820,1250,1100],VALUES[IND])]")
ps=ps.replace('l*1e-9/q:.12g','l*1e-9/q[{"lh":0,"l2":1,"l4":2}[n]]:.12g')
passive={'__file__':str(O/'spice_tolerance.py')};exec(ps,passive)
exec(s,ns);ns.update({k:passive[k] for k in ['F','run','VALUES']});ns['main']()
p=O/'simulation/end_to_end_results.json';d=json.loads(p.read_text());d['frequency_MHz']=[float(passive['F'][0]),150.0];d['temperature_scope']='DC algebra extrapolated to -50..30 C; no device operating qualification below -40 C or thermal/noise temperature validation';d['passive_Q_assumptions']={'Coilcraft':70,'APV':35,'frequency_MHz':50};d['noise_comparison']='Use simulation/upgrade/comparison.h5 for this mixed-inductor front end; no historical system-noise arrays relabeled as current.';p.write_text(json.dumps(d,indent=2)+'\n')

import h5py
with h5py.File(O/'simulation/end_to_end.h5') as h:
 f=h['frequency_MHz'][:];g=20*np.log10(abs(h['filter_s21'][:]));d['FM_filter_rejection_relative_to_best_30_55_dB_min']=float(g[(f>=30)&(f<=55)].max()-g[(f>=88)&(f<=108)].max())
p.write_text(json.dumps(d,indent=2)+'\n')
with h5py.File(O/"simulation/end_to_end.h5","a") as h:h.attrs["summary"]=json.dumps(d)
