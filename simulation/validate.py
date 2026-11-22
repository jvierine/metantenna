"""Run ngspice, tolerance sweeps and bias-tee loading checks locally.

No proprietary amplifier model is invented here. The active-device stage is
excluded from the filter validation; gain/noise/linearity remain bench gates.
"""
from pathlib import Path
import json, subprocess, tempfile
import numpy as np
import h5py
from design_filter import response

ROOT=Path(__file__).resolve().parents[1]
SIM=ROOT/'simulation'

def netlist(v, parasitic=True):
    ch,lh,c1,l2,c2,c3,l4,c4,c5=v
    lines=['Metantenna 50-ohm preselector; source voltage 2 V gives unity matched S21',
           'Vsrc src 0 AC 2','Rsrc src a 50','Rload out 0 50']
    def cap(name,a,b,p):
        name='c'+name
        lines.extend([f'R{name} {a} {name}r 0.03',f'L{name} {name}r {name}l {0.5 if parasitic else 0.0001}n',f'C{name} {name}l {b} {p}p'])
    def ind(name,a,b,n):
        name='l'+name
        lines.extend([f'R{name} {a} {name}r {2*np.pi*50e6*n*1e-9/70}',f'L{name} {name}r {b} {n}n'])
        if parasitic: lines.append(f'C{name}par {a} {b} 0.1p')
    cap('hp1','a','b',ch); ind('hp','b','0',lh); cap('hp2','b','c',ch)
    cap('lp1','c','0',c1); ind('lp2','c','d',l2); cap('lp2','c','d',c2)
    cap('lp3','d','0',c3); ind('lp4','d','out',l4); cap('lp4','d','out',c4); cap('lp5','out','0',c5)
    if parasitic:
        for n in ['a','b','c','d','out']: lines.append(f'Cpad{n} {n} 0 0.3p')
    lines.extend(['.control','set wr_singlescale','set wr_vecnames','ac lin 3991 1Meg 400Meg','let transfer = v(out)','let reflection = v(a)-1','wrdata response.txt real(transfer) imag(transfer) real(reflection) imag(reflection)','quit','.endc','.end'])
    return '\n'.join(lines)+'\n'

def run_spice(v,parasitic=True):
    with tempfile.TemporaryDirectory(prefix='metantenna-spice-') as td:
        p=Path(td); (p/'filter.cir').write_text(netlist(v,parasitic))
        r=subprocess.run(['ngspice','-b','filter.cir'],cwd=p,capture_output=True,text=True,check=True)
        a=np.loadtxt(p/'response.txt',skiprows=1)
        return a[:,0]/1e6,a[:,1]+1j*a[:,2],a[:,3]+1j*a[:,4],r.stdout+r.stderr

def main():
    v=np.array(json.loads((SIM/'filter_values.json').read_text())['preferred'])
    (SIM/'preselector.cir').write_text(netlist(v))
    f,s,r,log=run_spice(v)
    (SIM/'ngspice.log').write_text(log)
    f0,s0,_,_=run_spice(v,False)
    predicted=response(f0,v)[0]
    assert np.max(abs(s0-predicted))<2e-5, 'Independent ABCD/SPICE agreement failed'
    rng=np.random.default_rng(3255)
    # 300 simultaneous, uniformly distributed independent tolerances.
    # +/-2% inductors, +/-1% capacitors; includes the same nominal pad/ESL model.
    tol=np.array([.01,.02,.01,.02,.01,.01,.02,.01,.01])
    curves=[]
    for _ in range(300):
        _,ss,_,_=run_spice(v*(1+rng.uniform(-1,1,len(v))*tol))
        curves.append(20*np.log10(abs(ss)))
    curves=np.array(curves); db=20*np.log10(abs(s))
    band=(f>=30)&(f<=70); fm=(f>=88)&(f<=108)
    # Passive symmetrical bias tee: 1 uH choke, 0.5 pF SRF model,
    # 1 nF series DC block with 0.5 nH ESL; supply is RF-grounded.
    w=2*np.pi*f*1e6
    zc=.05+1j*w*.5e-9+1/(1j*w*1e-9)
    zl=1/(1/(.7+1j*w*1e-6)+1j*w*.5e-12)
    tee=2/(2+zc/50+50/zl+zc/zl)
    result={
        'status':'PASSIVE SIMULATION ONLY; prototype, not field-qualified',
        'ngspice_version':subprocess.run(['ngspice','--version'],capture_output=True,text=True).stdout.splitlines()[1:3],
        'nominal_insertion_loss_30_70_dB_max':float(-db[band].min()),
        'nominal_FM_rejection_dB_min':float(-db[fm].max()),
        'monte_carlo_trials':300,
        'monte_carlo_passband_loss_dB_worst':float(-curves[:,band].min()),
        'monte_carlo_FM_rejection_dB_worst':float(-curves[:,fm].max()),
        'one_bias_tee_loss_dB_max':float(-20*np.log10(abs(tee[band])).min()),
        'spot_filter_gain_dB':{str(x):float(np.interp(x,f,db)) for x in [30,32.55,36.2,49.92,53.5,70,88,98,108]},
        'limits':'No measured antenna impedance, vendor MMIC model, PCB EM coupling, humidity or thermal qualification. Monte Carlo is not exhaustive worst-case analysis.'}
    with h5py.File(SIM/'validation.h5','w') as h:
        h['frequency_MHz']=f; h['s21']=s; h['s11']=r; h['monte_carlo_s21_dB']=curves; h['bias_tee_s21']=tee
        for key,value in result.items(): h.attrs[key]=json.dumps(value)
    (SIM/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['nominal_insertion_loss_30_70_dB_max']<1.5
    assert result['monte_carlo_FM_rejection_dB_worst']>20
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
