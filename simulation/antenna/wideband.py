"""Reproduce NEC2 impedance tables on an exact50kHz grid, both X/Y ports.
Per-arm quantities use the virtual midpoint of equal/opposite differential
excitation; they are NOT independent arm-to-earth impedances.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import sys,subprocess,tempfile,re,json,hashlib
import numpy as np,h5py
from model import deck,NEC,ROOT
OUT=ROOT/'models/nec';OUT.mkdir(parents=True,exist_ok=True)
F=np.arange(2,3001,dtype=np.int64)*.05

def make_deck(length,pol,segments=41,frequencies=None):
 text=deck(length=length,angle=25,height=2,frequencies=[.1],segments=segments,pattern=False)
 if pol=='Y':text=text.replace('LD 4 4 2 2 50 0','LD 4 1 2 2 50 0').replace('EX 0 1 2 0 1 0','EX 0 4 2 0 1 0')
 pos=text.index('FR ');text=text[:pos]
 if frequencies is None:text+='FR 0 2999 0 0 .1 .05\nRP 0 1 1 1000 0 0 0 0\n'
 else:
  for f in frequencies:text+=f'FR 0 1 0 0 {f:.8g} 0\nRP 0 1 1 1000 0 0 0 0\n'
 return text+'EN\n'

def run(length,pol,segments=41,frequencies=None):
 d=make_deck(length,pol,segments,frequencies)
 with tempfile.TemporaryDirectory(prefix='open-antenna-nec-') as td:
  p=Path(td);(p/'model.nec').write_text(d)
  result=subprocess.run([NEC,'-i','model.nec','-o','model.out'],cwd=p,capture_output=True,text=True,timeout=1200)
  if result.returncode:raise RuntimeError(result.stderr)
  raw=(p/'model.out').read_text()
 tag=1 if pol=='X' else 4;zs=[]
 for block in raw.split('ANTENNA INPUT PARAMETERS')[1:]:
  row=next(l for l in block.split('RADIATION PATTERNS')[0].splitlines() if re.match(r'\s+%d\s+\d+\s+[-\d.]'%tag,l));v=list(map(float,row.split()));zs.append(complex(v[6],v[7]))
 z=np.array(zs);expected=2999 if frequencies is None else len(frequencies)
 assert len(z)==expected,(length,pol,len(z),expected)
 assert np.isfinite(z).all(),(length,pol,'nonfinite')
 return length,pol,z,d

jobs=[(l,p) for l in [1.,1.5,2.] for p in ['X','Y']];data={}
with ThreadPoolExecutor(max_workers=3) as pool:
 futures=[pool.submit(run,*j) for j in jobs]
 for task in as_completed(futures):
  l,p,z,d=task.result();data[l,p]=z;(OUT/f'arms_{l:g}m_{p}.nec').write_text(d)
  print(l,p,'done; negativeR samples',int((z.real<0).sum()),flush=True)
spots=np.array([.1,.15,.5,1.,10.,30.,50.,100.,150.]);checks={}
with ThreadPoolExecutor(max_workers=3) as pool:
 fs=[pool.submit(run,l,p,61,spots) for l,p in jobs]
 for task in as_completed(fs):
  l,p,z,_=task.result();i=np.rint((spots-.1)/.05).astype(int);base=data[l,p][i]
  err=abs(z-base)/np.maximum(abs(z),1e-12);checks[f'{l:g}m_{p}']={'frequency_MHz':spots.tolist(),'Z_61_real':z.real.tolist(),'Z_61_imag':z.imag.tolist(),'relative_complex_difference':err.tolist(),'maximum_relative_difference':float(err.max())}
with h5py.File(OUT/'crossed_dipole_impedance_0p1_150MHz.h5','w') as h:
 h['frequency_Hz']=np.arange(2,3001,dtype=np.int64)*50000;h['frequency_MHz']=F
 h['polarization']=np.array(['X','Y'],dtype=h5py.string_dtype());h['arm']=np.array(['negative','positive'],dtype=h5py.string_dtype())
 for l in [1.,1.5,2.]:
  g=h.create_group(f'arms_{l:g}m');z=np.stack([data[l,'X'],data[l,'Y']],axis=1)
  d=g.create_dataset('feedpoint_impedance_ohm',data=z,compression='gzip',shuffle=True);d.attrs['dimensions']='frequency,polarization';d.attrs['reference']='balanced voltage Vpositive-Vnegative divided by current entering positive terminal'
  a=g.create_dataset('arm_half_circuit_impedance_ohm',data=np.repeat((z/2)[:,:,None],2,axis=2),compression='gzip',shuffle=True);a.attrs['dimensions']='frequency,polarization,arm';a.attrs['definition']='Zfeed/2 for symmetric differential excitation about virtual electrical midpoint; not independent arm-to-earth Z'
  g.create_dataset('nonnegative_resistance',data=z.real>=0,compression='gzip')
  g.attrs.update(arm_length_m=l,feed_height_X_m=2.,feed_height_Y_m=2.01,slope_down_deg=25.,wire_radius_m=.001,feed_terminal_spacing_m=.086,segments_per_arm=41,segments_per_feed_bridge=3,orthogonal_port_termination_ohm=50.,soil_relative_permittivity=13.,soil_conductivity_S_per_m=.005)
  c=g.create_group('convergence_61_segments');c['frequency_MHz']=spots
  c['feedpoint_impedance_ohm']=np.stack([np.array(checks[f'{l:g}m_{p}']['Z_61_real'])+1j*np.array(checks[f'{l:g}m_{p}']['Z_61_imag']) for p in ['X','Y']],axis=1)
  c['relative_complex_difference']=np.stack([checks[f'{l:g}m_{p}']['relative_complex_difference'] for p in ['X','Y']],axis=1)
 h.attrs.update(solver='nec2c NEC2, double precision',solver_revision=subprocess.check_output(['git','-C',str(Path(NEC).parent),'rev-parse','HEAD'],text=True).strip(),solver_binary_sha256=hashlib.sha256(Path(NEC).read_bytes()).hexdigest(),geometry='crossed inverted V; nonconducting mast; homogeneous Sommerfeld-Norton ground; copper5.8e7S/m',frequency_step_Hz=50000,n_frequencies=2999,arm_definition='length of EACH wire arm; full dipole has two arms plus86mmfeedbridge',limits='Thin-wire model; noPCB,feedline,common-modebox,inhomogeneousground,orionosphericmodel; mesh convergence sampled only; output precision limited by NEC text formatting')
(OUT/'convergence.json').write_text(json.dumps(checks,indent=2)+'\n')
# Reopen delivered product and verify axes, symmetry definition and passivity.
with h5py.File(OUT/'crossed_dipole_impedance_0p1_150MHz.h5') as h:
 assert np.array_equal(np.diff(h['frequency_Hz'][:]),np.full(2998,50000))
 for l in [1.,1.5,2.]:
  g=h[f'arms_{l:g}m'];assert g['feedpoint_impedance_ohm'].shape==(2999,2)
  assert np.allclose(g['arm_half_circuit_impedance_ohm'][:,:,0]*2,g['feedpoint_impedance_ohm'][:])
  assert g['nonnegative_resistance'][:].all(),(l,'NEC passivity failure; inspect rawdata')
print('Complete HDF5',flush=True)
