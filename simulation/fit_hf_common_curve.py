"""Passive magnitude-only fit to approximate points read from Linekey's 202Y graph.

This constrains common-mode behavior only. It cannot determine leakage,
differential insertion loss, phase uniquely, or ferrite nonlinearity.
"""
from pathlib import Path
import json,numpy as np,h5py
from scipy.optimize import least_squares
R=Path(__file__).resolve().parents[1];out=R/'simulation/hf_choke';out.mkdir(exist_ok=True)
f=np.array([.1,.2,.3,.5,1,1.5,2,3,5,10,20,30,50,100])*1e6
z=np.array([.70,1.45,2.25,3.8,6.8,8.5,8.4,7.1,5.2,3.3,2.25,1.8,1.35,1.0])*1000
# Two series parallel-RLC branches; fixture has the two windings in parallel.
def impedance(q,ff):
 w=2*np.pi*ff
 return .21+sum(1/(1/r+1/(1j*w*l)+1j*w*c) for l,r,c in np.asarray(q).reshape(2,3))
lo=np.log([1e-3,1000,1e-12,.1e-6,100,.1e-12]);hi=np.log([2.5e-3,50000,100e-12,100e-6,10000,100e-12])
q=least_squares(lambda v:np.log(abs(impedance(np.exp(v),f))/z),np.log([1.1e-3,8500,7e-12,10e-6,1500,1e-12]),bounds=(lo,hi),max_nfev=20000)
params=np.exp(q.x);err=abs(abs(impedance(params,f))/z-1)
result={'source':'Linekey CLF series datasheet, 202Y typical common-mode graph; JLC C2941480','data_type':'Approximate hand-read graph points, not raw measurements; allow digitization uncertainty.', 'model':'Two series parallel-RLC branches plus0.21ohm fixture DC resistance. Nonunique magnitude fit; not vendor model.', 'branches':[{'L_H':float(a),'R_ohm':float(b),'C_F':float(c)} for a,b,c in params.reshape(2,3)],'max_relative_graph_fit_error':float(err.max()),'inferred_common_mode_L_H':float(params[0]+params[3]),'not_determined':['leakage inductance','inter-winding capacitance','differential S-parameters','phase uniquely','nonlinear behavior']}
(out/'common_mode_fit.json').write_text(json.dumps(result,indent=2)+'\n')
with h5py.File(out/'common_mode_graph.h5','w') as h:
 h['frequency_Hz']=f;h['approximate_graph_Z_ohm']=z;h['fitted_Z_ohm']=impedance(params,f)
 h.attrs['metadata']=json.dumps(result)
print(json.dumps(result,indent=2))
