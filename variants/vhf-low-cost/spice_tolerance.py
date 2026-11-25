"""Matched two-port ngspice tolerance runs and passive noise-wave G/T model.
All data/provenance in HDF5/JSON; no script credits in rendered figures.
"""
from pathlib import Path
import concurrent.futures as cf,subprocess,tempfile,json,hashlib,sys
import numpy as np,h5py
O=Path(__file__).resolve().parent;R=O.parents[1];D=O/'simulation/spice_tolerance';D.mkdir(exist_ok=True)
N=500;SEED=25503255
# Independent actual HP capacitors, followed by the LP ladder and input DC block.
VALUES=np.array([160,220,160,36,100,33,75,120,20,43,2400.])
# Verify nominal values against both maintained CAD assembly descriptions.
import re
refs=['C101','L101','C102','C103','L102','C104','C105','L103','C106','C107','C115']
def value_at_scale(value,inductor):
 m=re.match(r'([0-9.]+)([pnu])',value);return float(m[1])*{'p':1e-12,'n':1e-9,'u':1e-6}[m[2]]/(1e-9 if inductor else 1e-12)
for source in [R/'vhf/hardware/preamp_layout.json',O/'hardware/preamp_layout.json']:
 parts={p['ref']:p for p in json.loads(source.read_text())['parts']}
 assert np.allclose([value_at_scale(parts[ref]['value'],ref.startswith('L')) for ref in refs],VALUES)
IND=[1,4,7];CAP=[i for i in range(11) if i not in IND]
F=np.linspace(5,150,2901);B=(F>=30)&(F<=55)
def deck(v,q,variant):
 lines=['Two reciprocal passive preselectors; 50 ohm port reference']
 cp=[.1,.1,.1] if variant=='original' else [1e12/((2*np.pi*f*1e6)**2*l*1e-9) for f,l in zip([820,1250,1100],VALUES[IND])]
 def circuit(prefix,reverse):
  def node(s):return '0' if s=='0' else prefix+s
  def cap(n,a,b,p):
   lines.extend([f'R{prefix}{n} {node(a)} {node(n+"r")} .03',f'L{prefix}{n} {node(n+"r")} {node(n+"l")} .5n',f'C{prefix}{n} {node(n+"l")} {node(b)} {p:.12g}p'])
  def ind(n,a,b,l,c):
   lines.extend([f'R{prefix}{n} {node(a)} {node(n+"r")} {2*np.pi*50e6*l*1e-9/q:.12g}',f'L{prefix}{n} {node(n+"r")} {node(b)} {l:.12g}n',f'C{prefix}{n} {node(a)} {node(b)} {c:.12g}p'])
  lines.extend([f'V{prefix} {prefix}src 0 AC 2',f'R{prefix}src {prefix}src {node("out" if reverse else "in")} 50',f'R{prefix}load {node("in" if reverse else "out")} 0 50'])
  cap('h1','in','b',v[0]);ind('lh','b','0',v[1],cp[0]);cap('h2','b','c',v[2]);cap('c1','c','0',v[3]);ind('l2','c','d',v[4],cp[1]);cap('c2','c','d',v[5]);cap('c3','d','0',v[6]);ind('l4','d','e',v[7],cp[2]);cap('c4','d','e',v[8]);cap('c5','e','0',v[9]);cap('block','e','out',v[10])
  for n in ['in','b','c','d','e','out']:lines.append(f'C{prefix}pad{n} {node(n)} 0 .3p')
 circuit('a',False);circuit('b',True)
 lines+=['.control','set wr_singlescale','set wr_vecnames','ac lin 2901 5Meg 150Meg','let s11=v(ain)-1','let s21=v(aout)','let s12=v(bin)','let s22=v(bout)-1','wrdata s.txt real(s11) imag(s11) real(s21) imag(s21) real(s12) imag(s12) real(s22) imag(s22)','quit','.endc','.end']
 return '\n'.join(lines)+'\n'
def run(job):
 variant,v,q=job;text=deck(v,q,variant)
 with tempfile.TemporaryDirectory(prefix='vhf-tolerance-') as td:
  p=Path(td);(p/'filter.cir').write_text(text);res=subprocess.run(['ngspice','-b','filter.cir'],cwd=p,capture_output=True,text=True,check=True)
  if not (p/'s.txt').exists():raise RuntimeError(res.stdout+res.stderr)
  a=np.loadtxt(p/'s.txt',skiprows=1)
 s=np.empty((len(F),2,2),complex)
 for j,(i,k) in enumerate([(0,0),(1,0),(0,1),(1,1)]):s[:,i,k]=a[:,1+2*j]+1j*a[:,2+2*j]
 assert np.max(abs(s[:,1,0]-s[:,0,1]))<2e-5
 # Add unchanged matched 0.5 dB balun before filter; all front-end parts at 290 K.
 t=10**(-.5/20);s[:,0,0]*=t*t;s[:,0,1]*=t;s[:,1,0]*=t
 return s

def receiver_temperature(s,gamma,post):
 # Bosma passive noise correlation C=T*(I-S*S^H), in wave-power kelvin.
 c=290*(np.eye(2)-s@np.swapaxes(s.conj(),-1,-2))
 assert np.linalg.eigvalsh(c).min()>-.01
 a=s[:,1,0]*gamma/(1-s[:,0,0]*gamma)
 g=abs(s[:,1,0])**2*(1-abs(gamma)**2)/abs(1-s[:,0,0]*gamma)**2
 no=(abs(a)**2*c[:,0,0]+c[:,1,1]+a*c[:,0,1]+a.conj()*c[:,1,0]).real
 assert no.min()>-.01
 return (np.maximum(no,0)+post)/g,g
# Reference checks: a matched attenuator gives Friis at a matched input;
# an ideal lossless matched two-port has no thermal noise.
s=np.zeros((1,2,2),complex);s[:,0,1]=s[:,1,0]=.8
te,g=receiver_temperature(s,np.zeros(1),np.array([250.]));assert abs(te[0]-(290*(1/.64-1)+250/.64))<1e-9
s[:,0,1]=s[:,1,0]=1;te,g=receiver_temperature(s,np.zeros(1),np.array([250.]));assert abs(te[0]-250)<1e-9
rng=np.random.default_rng(SEED);data={};summary={'edge_definition':'3 dB below each response maximum','runs_per_variant':N,'seed':SEED,'scope':'ngspice front end plus passive noise-wave calculation with fixed NEC/PyGDSM pattern and sky; unchanged matched unilateral amplifier noise assumptions. Not full vendor transistor, measured Q, PCB EM, or production-yield validation.','models':{}}
summary['assumptions']=json.loads((D/'assumptions.json').read_text())
summary['ngspice_version']=subprocess.check_output(['ngspice','--version'],text=True).splitlines()[1:4]
summary['CAD_sha256']={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'vhf/hardware/preamp_layout.json',O/'hardware/preamp_layout.json']}
with h5py.File(D/'results.h5','w') as h:
 h['frequency_MHz']=F
 for variant,q in [('original',70),('low_cost',35)]:
  tol=np.ones(11)*(.01 if variant=='original' else .05);tol[IND]=.02 if variant=='original' else .05;tol[-1]=.05
  samples=VALUES*(1+rng.uniform(-1,1,(N,11))*tol)
  jobs=[(variant,VALUES,q)]+[(variant,v,q) for v in samples]
  out=[]
  with cf.ThreadPoolExecutor(max_workers=4) as pool:
   for i,s in enumerate(pool.map(run,jobs)):
    out.append(s)
    if i and i%100==0:print(variant,i,'ngspice trials complete',flush=True)
  data[variant]=np.asarray(out);d=h.create_group(variant);d['sample_values']=samples;d['s_parameters']=data[variant];d['transmission_dB']=20*np.log10(abs(data[variant][:,:,1,0]));d.attrs['Q_assumed_at_50MHz']=q
  (D/(variant+'_nominal.cir')).write_text(deck(VALUES,q,variant))
  curves=d['transmission_dB'][:];lo,med,hi=np.percentile(curves[1:],[2.5,50,97.5],axis=0)
  d['p025_dB']=lo;d['median_dB']=med;d['p975_dB']=hi
  def edges(y):
   # Cutoffs at 3 dB below each response maximum; common balun loss cancels.
   peak=np.argmax(y);threshold=y[peak]-3;lower=np.flatnonzero(y[:peak]<threshold);upper=np.flatnonzero(y[peak:]<threshold)
   if not len(lower) or not len(upper):return [np.nan,np.nan]
   a=lower[-1];b=peak+upper[0]
   return [np.interp(threshold,y[a:a+2],F[a:a+2]),np.interp(threshold,y[b-1:b+1][::-1],F[b-1:b+1][::-1])]
  e=np.array([edges(y) for y in curves[1:]]);d['minus3dB_edges_relative_to_peak_MHz']=e
  summary['models'][variant]={'edge_MHz_percentiles_2p5_50_97p5':np.percentile(e,[2.5,50,97.5],axis=0).tolist(),'spot_transmission_dB':{str(ff):np.percentile(curves[1:,np.argmin(abs(F-ff))],[2.5,50,97.5]).tolist() for ff in [30,32.55,50,55]},'max_95percent_width_in_30_55_dB':float(np.max((hi-lo)[B]))}
 # Quality-factor sensitivity at nominal L/C, separate from tolerance percentiles.
 for q in [20,50]:h[f'low_cost_nominal_Q{q}']=run(('low_cost',VALUES,q))
 with h5py.File(R/'simulation/antenna/sky_noise.h5') as sky,h5py.File(R/'simulation/antenna/antenna_system.h5') as ant:
  ff=sky['frequency_MHz'][:];use=(ff>=30)&(ff<=55);ff=ff[use];h['antenna_frequency_MHz']=ff
  # Same post-filter amplifier, pi pad, coax and receiver assumptions for both.
  ga=10**(25.1/10);lp=10**(3/10);lc=10**((5*np.sqrt(ff/50))/10)
  post=290*(10**(.27)-1)+(lp-1)*290/ga+lp*((lc-1)*290+lc*290*(10**(.6)-1))/ga
  for geom in ['SIMONe_candidate','arms_1p0m','arms_1p5m','arms_2p0m']:
   z=ant[geom+'/impedance_ohm'][:][use];gamma=(z-50)/(z+50);gain=ant[geom+'/available_zenith_gain_dBi'][:][use]
   # The same geometry/pattern for both assemblies; existing orthogonal-port load retained.
   tx=sky[geom+'/sky_X_K'][:][use];ground=sky[geom+'/ground_and_loss_K'][:][use];temper={}
   for variant in data:
    res=[]
    for s in data[variant]:
     si=np.empty((len(ff),2,2),complex)
     for i in range(2):
      for j in range(2):si[:,i,j]=np.interp(ff,F,s[:,i,j].real)+1j*np.interp(ff,F,s[:,i,j].imag)
     te,_=receiver_temperature(si,gamma,post);res.append(tx+ground[:,None]+te[:,None])
    temper[variant]=np.asarray(res);g=h[variant].create_group(geom);g['system_temperature_K']=temper[variant];g['G_over_T_dB_per_K']=gain[None,:,None]-10*np.log10(temper[variant]);g['Tsys_over_Tsky']=temper[variant]/tx[None]
   # Compare independent paired draws; summarize the sidereal-day median at each f.
   delta=10*np.log10(temper['original']/temper['low_cost']);dd=h.create_group('comparison/'+geom);dd['G_over_T_change_dB']=delta
   daymed=np.median(delta[1:],axis=2);nom=np.median(delta[0],axis=1);dd['nominal_daily_median_change_dB']=nom;dd['percentiles_daily_median_change_dB']=np.percentile(daymed,[2.5,50,97.5],axis=0)
   summary.setdefault('G_over_T_change_low_minus_original_dB',{})[geom]={str(freq):{'actual_frequency_MHz':float(ff[i]),'nominal_daily_median':float(nom[i]),'tolerance_daily_median_percentiles':np.percentile(daymed[:,i],[2.5,50,97.5]).tolist()} for freq in [32.55,50] for i in [np.argmin(abs(ff-freq))]}
 h.attrs['metadata']=json.dumps(summary)
 h.attrs['passive_noise_model']='C=290*(I-S*S^H); complex NEC source reflections retained. Matched amp Te from NF=2.7dB at 100MHz extrapolated, no vendor noise parameters.'
 h.attrs['sky_sha256']=hashlib.sha256((R/'simulation/antenna/sky_noise.h5').read_bytes()).hexdigest()
(D/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

# Compact numeric products for repository storage and summarize Q sensitivity.
subprocess.run([sys.executable,str(O/"compact_spice_results.py")],check=True)
