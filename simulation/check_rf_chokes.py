"""TDK ACM4520-901 differential/common-mode screening in 50-ohm fixtures.

Parameters from TDK's May 23 2024 ACM4520 equivalent-circuit publication.
No PCB parasitics or nonlinear ferrite characterization; bench qualification
is still required. Sensitivity includes imperfect magnetic coupling.
"""
from pathlib import Path
import subprocess,tempfile,json
import numpy as np,h5py
R=Path(__file__).resolve().parents[1]
def model(k=1.,scale=1.):
 s=[]
 for tag,ip,op in [('p','ip','op'),('n','in','on')]:
  s += [f'Rin{tag} {ip} a{tag} .018',f'Lfirst{tag} a{tag} b{tag} {10.2*scale}n',f'Rfirst{tag} a{tag} b{tag} 9',f'Cfirst{tag} a{tag} b{tag} .01p',f'Lcore{tag} b{tag} c{tag} 1810n',f'Rcore{tag} b{tag} c{tag} 1460',f'Ccore{tag} b{tag} c{tag} .452p',f'Llast{tag} c{tag} d{tag} {10.2*scale}n',f'Rlast{tag} c{tag} d{tag} 9',f'Clast{tag} c{tag} d{tag} .01p',f'Rout{tag} d{tag} {op} .018',f'Rbypass{tag} a{tag} d{tag} 1g']
 s += [f'Kcore Lcorep Lcoren {k}', 'Riso1 bp bn 1g','Riso2 cp cn 1g',f'Cdiff cp cn {3.49*scale}p']
 return '\n'.join(s)
curves=[];summary=[];nominal=None
for k,scale in [(1,1),(.995,1),(.99,1),(.99,1.5)]:
 both=[]
 for mode in ['differential','common','reverse']:
  excitation=('V1 src 0 AC 1\nRs src ip 50\nVn in 0 0\nRload op on 50' if mode=='differential' else 'V1 src 0 AC 1\nRs src ip 50\nV2 srcn 0 AC 1\nRsn srcn in 50\nRloadp op 0 50\nRloadn on 0 50')
  if mode=='reverse':excitation='V1 src 0 AC 1\nRs src op 50\nVn on 0 0\nRload ip in 50'
  transfer='2*(v(ip)-v(in))' if mode=='reverse' else '2*(v(op)-v(on))' if mode=='differential' else 'v(op)+v(on)'
  reflection='2*v(op)-1' if mode=='reverse' else '2*v(ip)-1'
  deck=f'''RF choke screening
{excitation}
{model(k,scale)}
.control
set wr_singlescale
set wr_vecnames
ac dec 100 100k 100meg
let transfer={transfer}
let reflection={reflection}
wrdata response.txt transfer reflection
quit
.endc
.end
'''
  with tempfile.TemporaryDirectory() as td:
   q=Path(td);(q/'choke.cir').write_text(deck)
   subprocess.run(['ngspice','-b','choke.cir'],cwd=q,capture_output=True,check=True)
   z=np.loadtxt(q/'response.txt',skiprows=1)
  f=z[:,0];s21=z[:,1]+1j*z[:,2];s11=z[:,3]+1j*z[:,4];both.append((s21,s11))
 band=(f>=30e6)&(f<=55e6)
 loss=-20*np.log10(abs(both[0][0]));rl=-20*np.log10(abs(both[0][1]));cm=-20*np.log10(abs(both[1][0]))
 assert loss[band].max()<1 and rl[band].min()>10,(k,scale,loss[band].max(),rl[band].min())
 summary.append({'coupling':k,'parasitic_scale':scale,'VHF_loss_dB_max':float(loss[band].max()),'VHF_return_loss_dB_min':float(rl[band].min()),'VHF_CM_fixture_attenuation_dB_min':float(cm[band].min()),'CM_fixture_attenuation_100kHz_dB':float(cm[0])})
 curves.append([loss,rl,cm])
 if k==1 and scale==1:nominal=both
with h5py.File(R/'simulation/rf_chokes.h5','w') as h:
 h['s21']=nominal[0][0];h['s11']=nominal[0][1];h['s12']=nominal[2][0];h['s22']=nominal[2][1]
 h['frequency_Hz']=f;h['screening_curves_dB']=np.array(curves);h.attrs['cases']=json.dumps(summary)
 h.attrs['limits']='Vendor equivalent-circuit-based screening plus assumed coupling/parasitic variations. Not measured, not PCB EM, not nonlinear qualification. Weak 100kHz common-mode suppression: not an approved HF-band choke.'
(R/'simulation/rf_chokes_results.json').write_text(json.dumps({'cases':summary,'VHF_screening':'pass','HF_100kHz_suppression':'insufficient; requires a separately qualified LF choke stage for the HF variant'},indent=2)+'\n')
print(json.dumps(summary,indent=2))
