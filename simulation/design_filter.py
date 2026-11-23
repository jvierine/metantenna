"""Synthesize a small 50-ohm elliptic-style preselector using lossy LC networks.

Scientific results are stored in HDF5. This optimizer does not model the antenna,
amplifier noise/nonlinearity, PCB electromagnetic coupling, or component SRF.
"""
from pathlib import Path
import json
import numpy as np
import h5py
from scipy.optimize import differential_evolution, least_squares

ROOT = Path(__file__).resolve().parents[1]

def response(f, v, q=70):
    # HP series C, shunt L, series C; LP shunt C, series parallel LC,
    # shunt C, series parallel LC, shunt C. All normalized to 50 ohms.
    w=2*np.pi*np.asarray(f)*1e6
    ch,lh,c1,l2,c2,c3,l4,c4,c5=v
    def c(x): return 0.03+1/(1j*w*x*1e-12)
    def l(x): return 2*np.pi*50e6*x*1e-9/q+1j*w*x*1e-9
    z=[c(ch),l(lh),c(ch),c(c1),1/(1/l(l2)+1/c(c2)),c(c3),1/(1/l(l4)+1/c(c4)),c(c5)]
    a=np.ones_like(w,dtype=complex); b=np.zeros_like(a); d=a.copy(); cc=b.copy()
    for k,t in enumerate(z):
        if k in [0,2,4,6]: b,d=a*t+b,cc*t+d
        else: a,cc=a+b/t,cc+d/t
    s21=2/(a+b/50+cc*50+d)
    s11=(a+b/50-cc*50-d)/(a+b/50+cc*50+d)
    return s21,s11

def main():
    f=np.r_[np.linspace(30,55,81),np.linspace(88,108,41),np.linspace(115,150,15),[5,10,15]]
    def cost(log):
        v=np.exp(log); s,_=response(f,v)
        db=20*np.log10(abs(s))
        return (np.maximum(-db[:81]-.8,0)**2).mean()*300 + (np.maximum(db[81:122]+45,0)**2).mean()*5 + (np.maximum(db[122:137]+30,0)**2).mean()*2 + (np.maximum(db[137:]+[25,15,6],0)**2).mean() + (-db[:81]).mean()
    bounds=[(80,400),(150,1500),(10,200),(50,400),(5,150),(30,250),(50,400),(5,150),(10,200)]
    result=differential_evolution(cost,np.log(bounds),seed=32,popsize=18,maxiter=600,tol=1e-8,polish=True)
    ideal=np.exp(result.x)
    # E24 capacitors and E24 inductors; refine local discrete combinations later.
    e24=np.array([10,11,12,13,15,16,18,20,22,24,27,30,33,36,39,43,47,51,56,62,68,75,82,91])
    values=np.unique(np.r_[e24/10,e24,e24*10,e24*100])
    rounded=np.array([values[np.argmin(abs(np.log(values/x)))] for x in ideal])
    # Coordinate search on nearby preferred values, using exactly the same objective.
    for _ in range(8):
        for i in range(len(rounded)):
            pool=np.array([47,50,56,62,75,82,100,120,150,180,200,220,250,270,290,310,330,390,470,560,680,820]) if i in [1,3,6] else values
            options=pool[np.argsort(abs(np.log(pool/rounded[i])))[:5]]
            candidates=[]
            for x in options:
                a=rounded.copy(); a[i]=x; candidates.append((cost(np.log(a)),a))
            rounded=min(candidates,key=lambda a:a[0])[1]
    out={'names':['HP_C_pF','HP_L_nH','LP_C1_pF','LP_L2_nH','LP_C2_pF','LP_C3_pF','LP_L4_nH','LP_C4_pF','LP_C5_pF'],'optimized':ideal.tolist(),'preferred':rounded.tolist(),'objective':cost(np.log(rounded)),'inductor_Q_at_50MHz':70,'passband_MHz':[30,55],'FM_stopband_MHz':[88,108],'target_FM_rejection_dB':45}
    (ROOT/'simulation/filter_values.json').write_text(json.dumps(out,indent=2)+'\n')
    f=np.linspace(1,200,3981); s,r=response(f,rounded)
    with h5py.File(ROOT/'simulation/filter_design.h5','w') as h:
        h['frequency_MHz']=f; h['s21']=s; h['s11']=r
        h.attrs['model']='Lumped LC; Q=70 at 50 MHz; C ESR=0.03 ohm; 50-ohm ports'
    print(json.dumps(out,indent=2))
    for freq in [10,20,30,32.55,36.2,49.92,53.5,70,88,98,108]:
        print(freq,20*np.log10(abs(response([freq],rounded)[0][0])))

if __name__=='__main__': main()
