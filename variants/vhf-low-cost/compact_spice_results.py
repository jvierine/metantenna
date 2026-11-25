"""Compact the reproducible sweep and add nominal Q sensitivity to G/T."""
from pathlib import Path
import json,os
import h5py,numpy as np
O=Path(__file__).resolve().parent;R=O.parents[1];D=O/'simulation/spice_tolerance';p=D/'results.h5'
with h5py.File(p) as check:
 if 's_parameters' not in check['original']:
  print('Results already compact');raise SystemExit(0)
# Load only function definitions and deterministic checks, not Monte Carlo runs.
# exec globals/locals must coincide for helper function global references.
ns={'__file__':str(O/'spice_tolerance.py')};exec((O/'spice_tolerance.py').read_text().split('rng=np.random.default_rng')[0],ns)
receiver_temperature=ns['receiver_temperature']
summary=json.loads((D/'summary.json').read_text())
with h5py.File(p) as src,h5py.File(D/'compact.h5','w') as dst:
 def copy(a,b):
  for k,v in a.attrs.items():b.attrs[k]=v
  for k,v in a.items():
   if isinstance(v,h5py.Group):copy(v,b.create_group(k));continue
   data=v[:]
   if k=='s_parameters':
    b.create_dataset('s_parameters_nominal',data=data[0],compression='gzip',shuffle=True)
    data=data[:,::10];k='s_parameters_sampled'
   elif k in ['system_temperature_K','G_over_T_dB_per_K','Tsys_over_Tsky','G_over_T_change_dB'] and data.ndim==3:
    b.create_dataset(k+'_nominal_by_sidereal_time',data=data[0],compression='gzip',shuffle=True)
    data=np.median(data,axis=2);k+='_daily_median'
   b.create_dataset(k,data=data,compression='gzip',shuffle=True)
 copy(src,dst);F=src['frequency_MHz'][:];dst['s_parameter_frequency_MHz']=F[::10]
 with h5py.File(R/'simulation/antenna/sky_noise.h5') as sky,h5py.File(R/'simulation/antenna/antenna_system.h5') as ant:
  ff=sky['frequency_MHz'][:];use=(ff>=30)&(ff<=55);ff=ff[use]
  ga=10**(25.1/10);lp=10**(.3);lc=10**((5*np.sqrt(ff/50))/10);post=290*(10**(.27)-1)+(lp-1)*290/ga+lp*((lc-1)*290+lc*290*(10**(.6)-1))/ga
  for geom in ['SIMONe_candidate','arms_1p0m','arms_1p5m','arms_2p0m']:
   z=ant[geom+'/impedance_ohm'][:][use];gamma=(z-50)/(z+50);tx=sky[geom+'/sky_X_K'][:][use];ground=sky[geom+'/ground_and_loss_K'][:][use]
   old=src['original/'+geom+'/system_temperature_K'][0]
   for q in [20,50]:
    s=src[f'low_cost_nominal_Q{q}'][:];si=np.empty((len(ff),2,2),complex)
    for i in range(2):
     for j in range(2):si[:,i,j]=np.interp(ff,F,s[:,i,j].real)+1j*np.interp(ff,F,s[:,i,j].imag)
    te,_=receiver_temperature(si,gamma,post);new=tx+ground[:,None]+te[:,None];delta=np.median(10*np.log10(old/new),axis=1)
    dst['comparison/'+geom].create_dataset('nominal_change_assumed_Q'+str(q),data=delta)
    summary.setdefault('Q_sensitivity_G_over_T_change_dB',{}).setdefault(geom,{})[str(q)]={str(freq):float(delta[np.argmin(abs(ff-freq))]) for freq in [32.55,50]}
 summary['storage']='Full sampled L/C values, matched transmission for every trial; nominal full S, trial S on 0.5MHz grid; nominal sidereal-time G/T and daily median per trial. Numeric products compressed; rerun samples to recover full dense S.'
 dst.attrs['metadata']=json.dumps(summary)
os.replace(D/'compact.h5',p);(D/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('Compressed HDF5 MB:',p.stat().st_size/1e6)
