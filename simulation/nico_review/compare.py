"""Before/after ngspice check of actual reviewed component values.
MMIC is matched unilateral linear gain/NF, not a nonlinear vendor transistor
model. Comparisons are 50-ohm at the head's balun secondary and SMA output.
Cable, antenna, balun and indoor CM network are unchanged and excluded here.
"""
from pathlib import Path
import sys,subprocess,tempfile,json,hashlib,itertools,xml.etree.ElementTree as E
import numpy as np,h5py
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent));from validate import netlist
K=1.380649e-23

def read(name):
 r=E.parse(R/(name+'_netlist.xml')).getroot();p={c.get('ref'):c.findtext('value') for c in r.findall('components/comp')};nets={(x.get('ref'),x.get('pin')):n.get('name').lstrip('/') for n in r.findall('nets/net') for x in n.findall('node')};return p,nets

def capacitance(v):
 import re
 m=re.match(r'([\d.]+)([pnu])',v);return float(m[1])*{'p':1e-12,'n':1e-9,'u':1e-6}[m[2]]

def deck(parts,ch='X',tolerance=(1.,1.)):
 n=100 if ch=='X' else 200
 capv=lambda i:capacitance(parts[f'C{n+i}'])
 vals=[capv(1)*1e12,float(parts[f'L{n+1}'][:-1]),capv(3)*1e12,float(parts[f'L{n+2}'][:-1]),capv(4)*1e12,capv(5)*1e12,float(parts[f'L{n+3}'][:-1]),capv(6)*1e12,capv(7)*1e12]
 s=netlist(vals).split('.control')[0].replace('Rload out 0 50','')
 lines=[s,'.temp 16.85']
 def cap(n,a,b,c):lines.extend([f'R{n} {a} {n}r .03',f'L{n} {n}r {n}l .5n',f'C{n} {n}l {b} {c:.12g}'])
 if f'C{n+15}' in parts:cap('input','out','galin',capv(15)*tolerance[0])
 else:lines.append('Rdirect out galin 1e-9 temp=-273.149')
 lines+=['Rmatch galin 0 50 temp=-273.149',f'Rnoise vn 0 {(10**(.27)-1)*50/4}',f'Eamp oa 0 value={{ {2*10**(25.1/20)}*(v(galin)+v(vn)) }}','Rout oa ampout 50 temp=-273.149','Rbias ampout biasL 41.2','Lbias biasL biasR 1u','Rchoke biasR 0 1.8','Cchoke ampout 0 .5p']
 cap('output','ampout','padin',capv(8)*tolerance[1]);lines+=['Rpad1 padin 0 294','Rpad2 padin padout 18','Rpad3 padout 0 294'];cap('final','padout','rx',capv(9))
 lines+=['Rload rx 0 50 temp=-273.149','.control','set wr_singlescale','set wr_vecnames','ac lin 2999 100k 150Meg','let response=v(rx)','let reflection=v(a)-1','wrdata ac.txt real(response) imag(response) real(reflection) imag(reflection)','noise v(rx) Vsrc lin 2999 100k 150Meg','setplot noise1','wrdata noise.txt onoise_spectrum inoise_spectrum','quit','.endc','.end']
 return '\n'.join(lines)+'\n'

def run(p,ch='X',tol=(1.,1.)):
 text=deck(p,ch,tol)
 with tempfile.TemporaryDirectory(prefix='antenna-review-spice-') as td:
  d=Path(td);(d/'head.cir').write_text(text);q=subprocess.run(['ngspice','-b','head.cir'],cwd=d,capture_output=True,text=True,check=True)
  if not (d/'noise.txt').exists():raise RuntimeError(q.stdout+q.stderr)
  a=np.loadtxt(d/'ac.txt',skiprows=1);z=np.loadtxt(d/'noise.txt',skiprows=1)
 return a[:,0],a[:,1]+1j*a[:,2],a[:,3]+1j*a[:,4],z[:,1],z[:,2],text

def dc_ground_path(p,nets,ch):
 parent={x:x for x in nets.values()}
 def find(x):
  if parent[x]!=x:parent[x]=find(parent[x])
  return parent[x]
 for ref in p:
  if ref.startswith(('R','L')) and (ref,'1') in nets and (ref,'2') in nets:
   a,b=nets[ref,'1'],nets[ref,'2'];parent[find(a)]=find(b)
 n=100 if ch=='X' else 200
 return find(nets[f'U{n+1}','1'])==find('GND')

summary={'model':'ngspice linear unilateral matched GALI74+:25.1dB gain,2.7dB NF extrapolated from100MHz; not IP3/compression/stability qualification','scope':'head balun-secondary to SMA; 50ohm source/load; unchanged antenna,balun,cable,indoor CM network excluded','spots':{},'DC_input_to_ground_path':{}}
with h5py.File(R/'comparison.h5','w') as h:
 for name in ['before','after']:
  p,nets=read(name);f,g,s11,en,ein,text=run(p);band=(f>=30e6)&(f<=55e6);db=20*np.log10(abs(g));nf=10*np.log10(ein**2/(4*K*290*50))
  d=h.create_group(name);d['frequency_Hz']=f;d['s21']=g;d['s11']=s11;d['output_noise_V_per_sqrtHz']=en;d['input_referred_noise_V_per_sqrtHz']=ein;d['noise_figure_dB']=nf;d['gain_dB']=db
  d.attrs['netlist_sha256']=hashlib.sha256((R/(name+'_netlist.xml')).read_bytes()).hexdigest();(R/(name+'.cir')).write_text(text)
  summary['DC_input_to_ground_path'][name]={ch:dc_ground_path(p,nets,ch) for ch in 'XY'}
  for ff in [30,32.55,50,55,88,108]:
   i=np.argmin(abs(f-ff*1e6));summary['spots'].setdefault(str(ff),{})[name]={'gain_dB':float(db[i]),'noise_figure_dB':float(nf[i])}
  if name=='after':
   fy,gy,*_=run(p,'Y');assert np.max(abs(gy-g))<1e-10
   curves=[]
   for tol in itertools.product([.95,1.05],repeat=2):curves.append(20*np.log10(abs(run(p,tol=tol)[1])))
   d['coupling_cap_5percent_gain_dB']=np.array(curves)
   summary['cap_tolerance_gain_excursion_dB_max']=float(np.max(abs(np.array(curves)[:,band]-db[band])))
   summary['XY_RF_agreement']=True
 before=h['before/gain_dB'][:];after=h['after/gain_dB'][:];delta=after-before;h['gain_change_dB']=delta
 summary['gain_change_30_55_dB_minmax']=[float(delta[band].min()),float(delta[band].max())]
 summary['noise_figure_change_30_55_dB_minmax']=[float(np.min(h['after/noise_figure_dB'][:][band]-h['before/noise_figure_dB'][:][band])),float(np.max(h['after/noise_figure_dB'][:][band]-h['before/noise_figure_dB'][:][band]))]
 h.attrs['summary']=json.dumps(summary)
(R/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
