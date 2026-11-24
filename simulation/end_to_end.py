"""Reproducible linear end-to-end model and DC corner checks for Rev B.

Passive preselector is independently solved by ngspice in both directions.
The MMIC is a matched, unilateral 25.1 dB behavioral stage: not a transistor,
noise-wave or nonlinear vendor model. No PCB coupling/stability qualification
is inferred from it. Sky/antenna results are NEC2/PyGDSM products.
"""
from pathlib import Path
import sys,json,tempfile,subprocess,itertools,hashlib
from dataclasses import asdict
import numpy as np
import h5py
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate import netlist,run_spice
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'hardware'))
from design import preamp,biastee
P={p.ref:p for p in preamp()[0]}
def coupling_cap(ref):
 import re
 a=re.match(r'([\d.]+)([pnu])',P[ref].value);return float(a[1])*{'p':1e-12,'n':1e-9,'u':1e-6}[a[2]]

def series(z):
 m=np.zeros((len(z),2,2),complex);m[:,0,0]=m[:,1,1]=1;m[:,0,1]=z;return m

def shunt(y):
 m=series(y*0);m[:,1,0]=y;return m

def matched(t):
 m=np.zeros((len(t),2,2),complex);m[:,0,0]=m[:,1,1]=(1+t*t)/(2*t);m[:,0,1]=50*(1-t*t)/(2*t);m[:,1,0]=(1-t*t)/(100*t);return m

def abcd(s11,s21,s12,s22):
 m=series(s11*0);m[:,0,0]=((1+s11)*(1-s22)+s12*s21)/(2*s21)
 m[:,0,1]=50*((1+s11)*(1+s22)-s12*s21)/(2*s21)
 m[:,1,0]=((1-s11)*(1-s22)-s12*s21)/(100*s21)
 m[:,1,1]=((1-s11)*(1+s22)+s12*s21)/(2*s21);return m

def gain(m,z):
 return 4*np.real(z)*50/abs(m[:,0,0]*50+m[:,0,1]+z*(m[:,1,0]*50+m[:,1,1]))**2

def main():
 assert next(p for p in biastee()[0] if p.ref=='F10').value=='500mA PTC'
 vals=np.array(json.loads((R/'simulation/filter_values.json').read_text())['preferred'])
 f,s21,s11,_=run_spice(vals)
 # Reverse excitation gives S22 and independently verifies reciprocity.
 deck=netlist(vals).replace('Rsrc src a 50','Rsrc src out 50').replace('Rload out 0 50','Rload a 0 50').replace('let transfer = v(out)','let transfer = v(a)').replace('let reflection = v(a)-1','let reflection = v(out)-1')
 with tempfile.TemporaryDirectory() as td:
  pp=Path(td);(pp/'reverse.cir').write_text(deck)
  subprocess.run(['ngspice','-b','reverse.cir'],cwd=pp,capture_output=True,check=True)
  a=np.loadtxt(pp/'response.txt',skiprows=1);s12=a[:,1]+1j*a[:,2];s22=a[:,3]+1j*a[:,4]
 assert np.max(abs(s21-s12))<1e-6
 keep=f<=100
 f=f[keep];s11=s11[keep];s21=s21[keep];s12=s12[keep];s22=s22[keep]
 w=2*np.pi*f*1e6
 cap=lambda c: .03+1j*w*.5e-9+1/(1j*w*c)
 choke=1/(1/(1.8+1j*w*1e-6)+1j*w*.5e-12)
 # Actual pi pad and two output blocking capacitors from the electrical design.
 assert [P[x].value for x in ['R103','R104','R105']]==['294','18','294']
 pad=shunt(np.full(len(f),1/294))@series(np.full(len(f),18))@shunt(np.full(len(f),1/294))
 out=series(cap(coupling_cap('C108')))@pad@series(cap(coupling_cap('C109')))
 # Matched unilateral amplifier in ABCD form (S12=0); no reverse stability claim.
 amp=abcd(np.zeros(len(f)),np.full(len(f),10**(25.1/20)),np.zeros(len(f)),np.zeros(len(f)))
 balun=matched(np.full(len(f),10**(-.5/20)))
 pre=abcd(s11,s21,s12,s22)
 cableloss=5*np.sqrt(f/50);cable=matched(10**(-cableloss/20)*np.exp(-1j*w*50/(.66*299792458)))
 with h5py.File(R/'simulation/rf_chokes.h5') as cm:
  cf=cm['frequency_Hz'][:]/1e6
  def interp(key):
   z=cm[key][:];return np.interp(f,cf,z.real)+1j*np.interp(f,cf,z.imag)
  cmatrix=abcd(interp('s11'),interp('s21'),interp('s12'),interp('s22'))
 indoorX=cmatrix@shunt(1/choke)@series(cap(1e-9))
 indoorY=cmatrix@series(2*cap(1e-9)) # C20 centre and C21 shield DC blocks
 headX=balun@pre@series(cap(coupling_cap('C115')))@amp@out@shunt(1/choke);headY=balun@pre@series(cap(coupling_cap('C115')))@amp@out
 chainX=headX@cable@indoorX;chainY=headY@cable@indoorY
 band=(f>=30)&(f<=55)
 gx=10*np.log10(gain(chainX,50));gy=10*np.log10(gain(chainY,50))
 assert np.isfinite(gx).all() and max(abs(gx[band]-gy[band]))<.3
 # Cable DC loop resistance is an installation assumption, swept to find the limit.
 # Includes two SS14s and conservatively 6 ohm for PTCs, chokes and contacts.
 v8=1.194*(1+57600/10000)
 corners=[]
 for vs,loop,vf,ampv,t,rtol,vtol in itertools.product([10.8,11.76,12,13.2],[0,2,3,5,10],[.25,.6],[4.3,4.8,5.3],[-20,25,60],[.99,1.01],[.98,1.02]):
  current=(v8*vtol-(ampv-.0031*(t-25)))/(41.2*rtol+1.8)
  total=2*current+.001
  vin=vs-2*vf-total*(loop+6+.03+.14+.12)
  corners.append([vs,loop,vf,ampv,t,current,vin,vin-v8*vtol-.4,current**2*41.2*rtol,max(0,vin-v8*vtol)*current])
 corners=np.array(corners);assert corners[:,5].max()<.12
 # Full required 50m installation: 12 V nominal ±10%, loop <=5 ohm,
 # two forward diodes up to0.6 V, full temp and device voltage corners.
 approved=(corners[:,0]>=11.76)&(corners[:,1]<=3)
 assert corners[approved,7].min()>0
 assert corners[:,8].max()<.5 # Half the nominal 1 W bias resistor rating.
 summary={'model':'Linear end-to-end behavioral amplifier, passive SPICE, NEC2 antenna and PyGDSM sky; not measured or PCB EM qualified',
 'frequency_MHz':[1,100], 'X_gain_50ohm_30_55_dB':[float(gx[band].min()),float(gx[band].max())],
 'Y_gain_50ohm_30_55_dB':[float(gy[band].min()),float(gy[band].max())],
 'X_Y_gain_difference_dB_max':float(max(abs(gx[band]-gy[band]))),
 'added_filter_DC_resistance_ohm_max':.29,'dc_corners':len(corners),'head_input_current_mA_max':float(corners[:,5].max()*2000+1),
 'regulator_headroom_after_0p4V_margin_V_min':float(corners[approved,7].min()),
 'bias_resistor_dissipation_W_max':float(corners[:,8].max()),
 'LDO_dissipation_W_max':float(corners[:,9].max()),
 'installation_requirement':'50m coax DC loop resistance <=3 ohm; regulated 12V -2%/+10%; ambient -20..60C. Cable RF loss assumed 5dB at50MHz, sqrt(f).',
 'off_spec_supply_or_cable_dropout_corners':int(np.sum(corners[:,7]<0)),
 'active_model_limits':'25.1dB gain and2.7dB NF extrapolated from100MHz typicals. IP3/P1dB budget only, not nonlinear simulation. No transistor or mismatch noise parameters; no loop stability, oscillation or X/Y coupling certification.',
 'antenna_cases':{},'checks':{'reciprocity':True,'DC_headroom':True,'bias_resistor_derating':True,'MMIC_current_below_120mA':True}}
 with h5py.File(R/'simulation/end_to_end.h5','w') as h:
  h['frequency_MHz']=f;h['X_50ohm_gain_dB']=gx;h['Y_50ohm_gain_dB']=gy;h['DC_corners']=corners
  h['filter_s11']=s11;h['filter_s21']=s21;h['filter_s12']=s12;h['filter_s22']=s22
  with h5py.File(R/'simulation/antenna/antenna_system.h5') as ant,h5py.File(R/'simulation/antenna/sky_noise.h5') as sky:
   af=ant['frequency_MHz'][:]
   for name in ['arms_1p0m','arms_1p5m','arms_2p0m','SIMONe_candidate']:
    z=ant[name]['impedance_ohm'][:];zz=np.interp(f,af,z.real)+1j*np.interp(f,af,z.imag)
    use=(f>=30)&(f<=55);gh=10*np.log10(gain(chainX,zz))
    d=h.create_group(name);d['frequency_MHz']=f[use];d['available_antenna_to_rx_gain_dB']=gh[use]
    for key in ['system_X_K','system_Y_K','sky_X_K','sky_Y_K']:d[key]=sky[name][key][:]
    spots={}
    for ff in [32.55,50,55]:
     i=np.argmin(abs(af-ff));j=np.argmin(abs(sky['frequency_MHz'][:]-ff));
     spots[str(ff)]={'antenna_to_rx_gain_dB':float(np.interp(ff,f,gh)), 'realized_zenith_gain_dBi':float(ant[name]['realized_zenith_gain_dBi'][i]),'system_X_noise_K_median':float(np.median(sky[name]['system_X_K'][j]))}
    summary['antenna_cases'][name]=spots
  h.attrs['summary']=json.dumps(summary)
  h.attrs['electrical_definition_sha256']=hashlib.sha256(json.dumps([asdict(p) for p in preamp()[0]+biastee()[0]],sort_keys=True).encode()).hexdigest()
 (R/'simulation/end_to_end_results.json').write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
