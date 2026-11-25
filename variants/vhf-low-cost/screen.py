"""Lumped filter sensitivity screening, not a vendor RF or nonlinear model."""
from pathlib import Path
import numpy as np,h5py,json
R=Path(__file__).resolve().parents[2];O=Path(__file__).resolve().parent
f=np.linspace(.1,150,2999);v=np.array([160,220,160,36,100,33,75,120,20,43.])
def response(v,q):
 w=2*np.pi*f*1e6
 def c(p):return .03+1/(1j*w*p*1e-12)
 def l(n):return 2*np.pi*50e6*n*1e-9/q+1j*w*n*1e-9
 ch,lh,ch2,c1,l2,c2,c3,l4,c4,c5=v
 z=[c(ch),l(lh),c(ch2),c(c1),1/(1/l(l2)+1/c(c2)),c(c3),1/(1/l(l4)+1/c(c4)),c(c5)]
 a=np.ones(len(f),complex);b=np.zeros_like(a);cc=b.copy();d=a.copy()
 for k,t in enumerate(z):
  if k in [0,2,4,6]:b,d=a*t+b,cc*t+d
  else:a,cc=a+b/t,cc+d/t
 return 2/(a+b/50+cc*50+d)
def db(g):return 20*np.log10(abs(g))
band=(f>=30)&(f<=55);fm=(f>=88)&(f<=108);rng=np.random.default_rng(12555)
baseline=db(response(v,70));results={'scope':'50-ohm lumped preselector only. Q at 50 MHz is an assumed sensitivity parameter, not guaranteed by catalogue Q at 250/500 MHz. No SPICE transistor, EM, choke, IP3 or transient validation.','trials':500,'spots':{}}
with h5py.File(O/'simulation/filter_screen.h5','w') as h:
 h['frequency_MHz']=f;h['baseline_Q70_s21_dB']=baseline
 for q in [20,35,50]:
  g=db(response(v,q));trials=np.array([db(response(v*rng.uniform(.95,1.05,len(v)),q)) for _ in range(500)])
  d=h.create_group('assumed_Q'+str(q));d['nominal_s21_dB']=g;d['tolerance_min_dB']=trials.min(0);d['tolerance_max_dB']=trials.max(0)
  results[str(q)]={'max_nominal_loss_30_55_dB':float(-g[band].min()),'extra_loss_dB_at_32p55':float(np.interp(32.55,f,baseline-g)),'extra_loss_dB_at_50':float(np.interp(50,f,baseline-g)),'worst_FM_rejection_in_500_trials_dB':float(-trials[:,fm].max()),'worst_loss_30_55_in_500_trials_dB':float(-trials[:,band].min())}
  # First-order incremental receiver noise with old sky/ground/antenna fixed.
  # Moving the entire old receiver contribution behind the extra passive loss
  # is conservative for that contribution. Does not recompute complex mismatch.
  with h5py.File(R/'simulation/antenna/sky_noise.h5') as sky,h5py.File(R/'simulation/antenna/antenna_system.h5') as ant:
   ff=sky['frequency_MHz'][:];extra=np.interp(ff,f,baseline-g);ratio=10**(extra/10)
   for name in ['SIMONe_candidate','arms_1p0m','arms_1p5m','arms_2p0m']:
    tau=ant[name+'/power_match_50ohm'][:];oldr=sky[name+'/receiver_equivalent_K'][:];oldsys=sky[name+'/system_X_K'][:]
    new=oldsys+(ratio-1)[:,None]*(oldr+290/np.maximum(tau,1e-12))[:,None]
    dd=d.create_group(name);dd['frequency_MHz']=ff;dd['incremental_G_over_T_penalty_dB']=10*np.log10(new/oldsys)
    i=np.argmin(abs(ff-32.55));results[str(q)].setdefault('G_over_T_penalty_at_nearest_32p55_dB',{})[name]=float(np.max(10*np.log10(new[i]/oldsys[i])))
 h.attrs['scope']=results['scope'];h.attrs['seed']=12555
(O/'simulation/summary.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))

# Independent ngspice check of the nominal linear filter implementation.
import sys
sys.path.insert(0,str(R/'simulation'))
from validate import run_spice,netlist
original_f=f.copy();agreement={}
with h5py.File(O/'simulation/spice_check.h5','w') as h:
 for qq in [20,35,50]:
  ff,ss,_,_=run_spice([160,220,36,100,33,75,120,20,43],False,qq)
  f=ff;pred=response(v,qq);err=float(np.max(abs(ss-pred)));assert err<2e-5,err
  d=h.create_group('Q'+str(qq));d['frequency_MHz']=ff;d['ngspice_s21']=ss;d.attrs['max_complex_difference']=err;agreement[str(qq)]=err
 f=original_f
(O/'simulation/spice_agreement.json').write_text(json.dumps(agreement,indent=2)+'\n')
(O/'simulation/filter_Q35.cir').write_text(netlist([160,220,36,100,33,75,120,20,43],False,35))
