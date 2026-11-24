"""Broad device-spread screening; no probability/yield interpretation."""
from pathlib import Path
import sys,re,json
import numpy as np,h5py
sys.path.insert(0,str(Path(__file__).resolve().parent))
from check import run
O=Path(__file__).resolve().parent
rows=[]
for idss in [.024,.040,.060]:
 for vto in [-2.,-3.65,-6.5]:
  a,n,log=run(idss/vto**2,vto);f=a[:,0]
  def value(key):return float(re.search(re.escape(key)+r'\s*=\s*([-+\d.eE]+)',log)[1])
  rows.append([idss,vto,value('v(sp)'),value('v(ep)'),-value('i(vdd)'),float(np.interp(1e6,f,n[:,1])*1e9),float(np.interp(30e6,f,n[:,1])*1e9)])
rows=np.array(rows)
assert np.isfinite(rows).all() and (rows[:,2]>rows[:,3]).all() and rows[:,3].min()>0
with h5py.File(O/'corners.h5','w') as h:
 h['corners']=rows;h.attrs['columns']='Idss_A,Vto_V,source_V,emitter_V,buffers_current_A_per_polarization,en_1MHz_nV,en_30MHz_nV'
summary={'corners':len(rows),'two_polarization_buffers_current_A_max':float(2*rows[:,4].max()),'emitter_bias_V_min':float(rows[:,3].min()),'status':'Genericmodel screening; asymmetric device mismatch,temperature,nonlinearblocking,andGALIcurrentmustalsoqualify'}
(O/'corners.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary)
