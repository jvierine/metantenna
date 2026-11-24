"""CLF9060-202Y HF design screening using ngspice, not a vendor SPICE model.

Published: 2mH +/-50%, DCR<=0.42ohm, 0.6A, CM impedance>=3kohm
from1 to5MHz. Source: Linekey CLF series datasheet supplied by JLC C2941480.
Common-mode loss/self capacitance are magnitude-fitted to the datasheet
graph. Coupling and inter-winding capacitance remain ASSUMED sensitivity
parameters: no vendor leakage/S-parameter data were supplied.
"""
from pathlib import Path
import subprocess,tempfile,itertools,json,hashlib
import numpy as np,h5py
R=Path(__file__).resolve().parents[1]
FIT=json.loads((R/'simulation/hf_choke/common_mode_fit.json').read_text())
FIT_L=sum(x['L_H'] for x in FIT['branches'])

def deck(L,k,cself,cinter,mode):
 lines=['CLF9060-202Y sensitivity screening']
 if mode=='DM':lines+=['V1 src 0 AC 1','Rs src ip 50','Vn inn 0 0','Rload op on 50']
 else:lines+=['V1 src 0 AC 1','Rs src ip 50','V2 srcn 0 AC 1','Rsn srcn inn 50','Rloadp op 0 50','Rloadn on 0 50']
 # Both windings are coupled; branch values reproduce the fitted parallel-
 # winding common-mode fixture for any assumed k. Leakage remains unknown.
 lines += ['RdcP ip ap .42','RdcN inn an .42']
 for i,branch in enumerate(FIT['branches']):
  leftp,leftn=('ap','an') if i==0 else ('midp','midn')
  rightp,rightn=('midp','midn') if i==0 else ('op','on')
  ll=branch['L_H']*(L/FIT_L)*2/(1+k)
  rr=branch['R_ohm']*2;cc=branch['C_F']*cself/2
  lines += [f'Lp{i} {leftp} {rightp} {ll}',f'Ln{i} {leftn} {rightn} {ll}',f'K{i} Lp{i} Ln{i} {k}',
            f'RlossP{i} {leftp} {rightp} {rr}',f'RlossN{i} {leftn} {rightn} {rr}',
            f'CselfP{i} {leftp} {rightp} {cc}',f'CselfN{i} {leftn} {rightn} {cc}']
 lines += [f'Cinter ap an {cinter}','Riso op on 1g']
 trans='2*(v(op)-v(on))' if mode=='DM' else 'v(op)+v(on)'
 lines += ['.control','set wr_singlescale','set wr_vecnames','ac dec 90 100k 50meg',f'let transfer={trans}',
           'let reflection=2*v(ip)-1','wrdata response.txt transfer reflection','quit','.endc','.end']
 return '\n'.join(lines)+'\n'

def main():
 cases=[];curves=[];complex_s=[]
 for L,k,cs,ci in itertools.product([.001,FIT_L,.002,.003],[1,.99999,.9999,.999,.99],[.7,1,1.3],[1e-12,5e-12,15e-12]):
  pair=[]
  for mode in ['DM','CM']:
   with tempfile.TemporaryDirectory() as td:
    p=Path(td);(p/'case.cir').write_text(deck(L,k,cs,ci,mode))
    run=subprocess.run(['ngspice','-b','case.cir'],cwd=p,capture_output=True,text=True)
    assert run.returncode==0,run.stdout+run.stderr
    a=np.loadtxt(p/'response.txt',skiprows=1)
   f=a[:,0];pair.append((a[:,1]+1j*a[:,2],a[:,3]+1j*a[:,4]))
  loss=-20*np.log10(abs(pair[0][0]));rl=-20*np.log10(abs(pair[0][1]));cm=-20*np.log10(abs(pair[1][0]))
  assert np.isfinite(loss).all() and np.isfinite(cm).all()
  cm_z=50*(1/pair[1][0]-1);specified=(f>=1e6)&(f<=5e6)
  assert abs(cm_z[specified]).min()>=3000,'Screening model violates published CM impedance minimum'
  usable=f<=30e6
  cases.append({'L_H':L,'coupling':k,'self_capacitance_scale':cs,'Cinter_F':ci,'DM_loss_max_dB':float(loss.max()),
                'DM_loss_50MHz_dB':float(loss[-1]),'DM_loss_30MHz_dB':float(np.interp(30e6,f,loss)),'DM_loss_0p1_30MHz_max_dB':float(loss[usable].max()),'return_loss_min_dB':float(rl.min()),'CM_attenuation_100kHz_dB':float(cm[0]),
                'screening_pass_1dB_10dB_RL':bool(loss[usable].max()<=1 and rl[usable].min()>=10)})
  curves.append([loss,rl,cm]);complex_s.append([pair[0][0],pair[0][1],pair[1][0]])
 out=R/'simulation/hf_choke';out.mkdir(exist_ok=True)
 (out/'example_DM.cir').write_text(deck(FIT_L,.9999,1,5e-12,'DM'))
 (out/'example_CM.cir').write_text(deck(FIT_L,.9999,1,5e-12,'CM'))
 with h5py.File(out/'screening.h5','w') as h:
  h['frequency_Hz']=f;h['curves_dB']=np.array(curves);h['complex_S']=np.array(complex_s)
  h.attrs['cases']=json.dumps(cases);h.attrs['model_type']='Assumption sensitivity model, NOT vendor characterized or measured.'
  h.attrs['fixture']='50ohm single-ended DM; CM source/load 50ohm per conductor to reference.'
 report={'part':'Linekey CLF9060-202Y','JLC':'C2941480','selected_for':'HF low-frequency common-mode development stage, one per polarization',
         'published':{'L_H':.002,'L_tolerance':.5,'DCR_ohm_max':.42,'current_A':.6,'CM_Z_ohm_min_1_to_5MHz':3000},
         'simulator':subprocess.check_output(['ngspice','--version'],text=True).splitlines()[1:4],
         'model_status':'Screening only; CM loss/self-capacitance network fitted to approximate datasheet graph; coupling and interwinding capacitance are assumed.',
         'common_mode_fit':FIT,'cases':len(cases),'screening_passes':sum(c['screening_pass_1dB_10dB_RL'] for c in cases),
         'release_status':'NOT approved for 0.1-30MHz RF path without measured/vendor differential data',
         'known_leakage_requirement':'Leakage and parasitics remain unknown; evaluate 0.1-30MHz usable band. An ideal K=1 model conceals high-frequency losses.',
         'DC_X_loop_drop_at_191mA_V_max_20C':2*.42*.191,
         'datasheet_source':'https://jlcpcb.com/partdetail/Linekey-CLF9060202Y/C2941480',
         'cases_detail':cases}
 (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='cases_detail'},indent=2))
 # Selected sensitivity examples for human-readable Rustplotlib figures.
 selections=[]
 for k in [.99999,.9999,.999]:
  idx=next(i for i,c in enumerate(cases) if c['L_H']==FIT_L and c['coupling']==k and c['self_capacitance_scale']==1 and c['Cinter_F']==5e-12)
  selections.append((idx,k))
 s='use anyhow::Result; use rustplotlib::*; fn main()->Result<()> { let mut f=ArticleLayout::new(177.,9.)?.figure(1.,90.)?;let p=f.grid(1,2)?;f.width_mm=177.;f.height_mm=96.;\n'
 for j in [0,1]:
  label='Differential insertion loss (dB)' if j==0 else r'Common-mode impedance ($\mathrm{k}\Omega$)'
  s+=f'f.panels[p[{j}]].rect=Rect::new({22+j*87}.,5.,62.,61.); f.panels[p[{j}]].axes=Some(Axes::new([0.1,30.],[0.,{16 if j==0 else 10}.],"Frequency (MHz)",{json.dumps(label)}));f.panels[p[{j}]].axes.as_mut().unwrap().set_xscale(AxisScale::Log10)?;\n'
  chosen=selections if j==0 else [(selections[1][0],0)]
  for idx,k in chosen:
   values=curves[idx][0] if j==0 else abs(50*(1/complex_s[idx][2]-1))/1000
   pts=[[float(x/1e6),float(y)] for x,y in zip(f[::3],values[::3])]
   label=f"k = {k}" if j==0 else "SPICE fit"
   s+=f'f.panels[p[{j}]].plot(vec!{str(pts).replace(" ","")},{json.dumps(label)});\n'
  if j==1:
   with h5py.File(out/'common_mode_graph.h5') as g:
    pts=[[float(x/1e6),float(y/1000)] for x,y in zip(g['frequency_Hz'][:],g['approximate_graph_Z_ohm'][:]) if x<=30e6]
   s+=f'f.panels[p[1]].plot(vec!{str(pts).replace(" ","")},"Datasheet (approx.)");\n'
  s+=f'f.panels[p[{j}]].legend.as_mut().unwrap().position=LegendPosition::{"UpperLeft" if j==0 else "LowerLeft"};\n'
 s+='for ext in ["png","svg","pdf"] {f.save(format!("hf/docs/hf_choke_screening.{ext}"))?;} Ok(())}\n'
 (R/'tools/plot/src/bin/hf_choke.rs').write_text(s)
if __name__=='__main__':main()
