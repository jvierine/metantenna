"""HF candidate SPICE: datasheet-constrained generic transistor models.
These are screening models, NOT vendor-validated nonlinear/noise models.
No claim of production IP3 or1.3sky qualification follows from this script.
"""
from pathlib import Path
import tempfile,subprocess,json
import numpy as np,h5py
R=Path(__file__).resolve().parents[2];O=Path(__file__).resolve().parent

def deck(beta=.003,vto=-3.65):
 s=['HF JFET/emitter follower screen','VDD vdd 0 6.0','VANT gp gn DC 0 AC 1',
 '.model J310 NJF (BETA=%g VTO=%g LAMBDA=.02 CGS=4.1p CGD=2p IS=1p)'%(beta,vto),
 '.model BC850 NPN (IS=6f BF=400 VAF=80 RB=50 RC=1 RE=.2 CJE=12p CJC=4p TF=.4n)']
 for side in ['p','n']:
  s += [f'RG{side} g{side} 0 1Meg',f'RD{side} vdd d{side} 10',f'CD{side} d{side} 0 100n',f'J{side} d{side} g{side} s{side} J310',f'RS{side} s{side} 0 180',f'Q{side} vdd s{side} e{side} BC850',f'RE{side} e{side} 0 220',f'CC{side} e{side} c{side} 220n',f'RO{side} c{side} t{side} 2.2']
 s += ['LP tp tn 1m','LS sec 0 1m','KX LP LS 1','RREF tn 0 1T TEMP=-273.149','RTERM sec hp0 39','CH1 hp0 hp1 33n','LH hp1 0 39u','CH2 hp1 lp0 33n',
 'L1 lp0 lp1 120n','C1 lp1 0 130p','L2 lp1 lp2 470n','C2 lp2 0 220p','L3 lp2 lp3 470n','C3 lp3 0 130p','L4 lp3 amp_in 120n','RIN amp_in 0 50 TEMP=-273.149',
 # Matched MMIC gain25.1dB; RIN is noiseless numerical termination.
 # RNOISE=Te*50/(4*290) because terminal signal is half open-source voltage.
 # This avoids double-counting physical50ohm termination thermal noise.
 'RNOISE nv 0 10.8','EAMP ao 0 VALUE={35.98*(v(amp_in)+v(nv))}','ROUT ao ab 50','CB ab pi1 220n','RP1 pi1 0 294','RP2 pi1 pi2 18','RP3 pi2 0 294','CO pi2 load 220n','RLOAD load 0 50',
 '.control','set wr_singlescale','set wr_vecnames','op','print v(sp) v(sn) v(ep) v(en) i(VDD)','ac dec 100 10k 150Meg','let zin=-1/i(VANT)','wrdata ac.txt real(v(load)) imag(v(load)) real(zin) imag(zin)',
 'noise v(load) VANT dec 100 10k 150Meg','setplot noise1','wrdata noise.txt inoise_spectrum onoise_spectrum','quit','.endc','.end']
 return '\n'.join(s)+'\n'

def run(b=.003,v=-3.65):
 with tempfile.TemporaryDirectory() as td:
  p=Path(td);(p/'a.cir').write_text(deck(b,v));r=subprocess.run(['ngspice','-b','a.cir'],cwd=p,capture_output=True,text=True)
  if r.returncode:raise RuntimeError(r.stdout+r.stderr)
  return np.loadtxt(p/'ac.txt',skiprows=1),np.loadtxt(p/'noise.txt',skiprows=1),r.stdout+r.stderr
(O/'candidate.cir').write_text(deck());a,n,log=run();(O/'screening.log').write_text(log)
assert np.isfinite(a).all() and np.isfinite(n).all()
f=a[:,0];gain=a[:,1]+1j*a[:,2]
with h5py.File(O/'screening.h5','w') as h:
 h['frequency_Hz']=f;h['voltage_gain']=gain;h['differential_input_impedance_ohm']=a[:,3]+1j*a[:,4];h['input_voltage_noise_V_per_sqrtHz']=n[:,1]
 h.attrs['status']='Generic transistor and matchedMMICscreening;notqualified;noantenna-source-noisewaveorPCBEMmodel'
metrics={'status':'screening only; HF board NOT manufacturing released','model':'GenericNJFBETA.003,VTO-3.65;genericBC850;idealtransformer;matchedbehavioralGALI','spots':{}}
for ff in [1e5,1e6,10e6,30e6]:
 i=np.argmin(abs(f-ff));metrics['spots'][str(ff)]={'voltage_gain_dB':float(20*np.log10(abs(gain[i]))),'shorted_input_referred_noise_nV_per_sqrtHz':float(n[i,1]*1e9),'input_impedance_ohm':[float(a[i,3]),float(a[i,4])]}
(O/'results.json').write_text(json.dumps(metrics,indent=2)+'\n');print(json.dumps(metrics,indent=2))
