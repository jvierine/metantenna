"""Reproducible eight-way filter-inductor upgrade screen; numeric products in HDF5."""
from pathlib import Path
import json,itertools
import numpy as np,h5py
p=Path(__file__).with_name('spice_tolerance.py')
s=p.read_text().split('rng=np.random.default_rng')[0]
s=s.replace("cp=[.1,.1,.1] if variant=='original' else [1e12/((2*np.pi*f*1e6)**2*l*1e-9) for f,l in zip([820,1250,1100],VALUES[IND])]", "cp=[.1 if flag else 1e12/((2*np.pi*f*1e6)**2*l*1e-9) for flag,f,l in zip(variant,[820,1250,1100],VALUES[IND])]")
s=s.replace('l*1e-9/q:.12g','l*1e-9/q[{"lh":0,"l2":1,"l4":2}[n]]:.12g')
ns={'__file__':str(p)};exec(s,ns)
F=ns['F'];run=ns['run'];rv=ns['receiver_temperature'];R=ns['R']
ff=np.arange(30,55.001,.05)
with h5py.File(R/'simulation/antenna/sky_noise.h5') as sky,h5py.File(R/'simulation/antenna/antenna_system.h5') as ant:
 sf=sky['frequency_MHz'][:];use=(sf>=30)&(sf<=55);ff=sf[use]
 ga=10**2.51;lp=10**.3;lc=10**((5*np.sqrt(ff/50))/10);post=290*(10**.27-1)+(lp-1)*290/ga+lp*((lc-1)*290+lc*290*(10**.6-1))/ga
 out={};temps={}
 for mask in itertools.product([False,True],repeat=3):
  ss=run((mask,ns['VALUES'],[70 if a else 35 for a in mask]));si=np.empty((len(ff),2,2),complex)
  for i in range(2):
   for j in range(2):si[:,i,j]=np.interp(ff,F,ss[:,i,j].real)+1j*np.interp(ff,F,ss[:,i,j].imag)
  k=''.join('1' if a else '0' for a in mask);out[k]={};temps[k]={}
  for geom in ['SIMONe_candidate','arms_1p0m','arms_1p5m','arms_2p0m']:
   z=ant[geom+'/impedance_ohm'][:][use];te,_=rv(si,(z-50)/(z+50),post);t=sky[geom+'/sky_X_K'][:][use]+sky[geom+'/ground_and_loss_K'][:][use,None]+te[:,None];temps[k][geom]=t
   base=temps['000'][geom];delta=np.median(10*np.log10(base/t),axis=1)
   out[k][geom]={str(f):float(delta[np.argmin(abs(ff-f))]) for f in [32.55,50,55]}
 result={'scope':'Nominal ngspice ranking only. Q=35 cheap and 70 upgraded at 50 MHz are assumptions, not measured data. Existing NEC/PyGDSM source and noise model retained. Not a temperature qualification.','mask_order':['L101/L201 220nH','L102/L202 100nH','L103/L203 120nH'],'selected_mask':'101','G_over_T_improvement_over_cheapest_dB':out,'incremental_parts_cost_usd':{'reference_quantity':10,'selected_Coilcraft_total':2*(1.1696+1.1381),'removed_APV_allowance':[2*(.0436+.04),2*(.0458+.08)],'net_increment_range':[2*(1.1696+1.1381)-2*(.0458+.08),2*(1.1696+1.1381)-2*(.0436+.04)],'price_scope':'LCSC quantity-10 catalogue prices checked 2026-11-25, not JLC checkout quote or assembly fees','sources':['https://www.lcsc.com/product-image/C40877572.html','https://www.lcsc.com/product-detail/C43831062.html']}}
 dest=p.parent/'simulation/upgrade';dest.mkdir(exist_ok=True)
 (dest/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
 with h5py.File(dest/'comparison.h5','w') as h:
  h['frequency_MHz']=ff;h.attrs['metadata']=json.dumps(result)
  for mask,geoms in temps.items():
   for geom,t in geoms.items():h.create_dataset(mask+'/'+geom+'/system_temperature_K',data=t,compression='gzip')
 print(json.dumps(result,indent=2))
