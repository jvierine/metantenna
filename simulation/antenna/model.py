"""NEC2 crossed inverted-V model; figures are generated separately with Rustplotlib.

Provenance: nec2c KJ7LNW/nec2c; see run_metadata.json for exact revision.
Plastic mast and 2 mm bare copper wire. Feed spans represent the 86 mm board
terminal spacing, not a PCB electromagnetic model. Y port is terminated in
50 ohms. The two feed bridges are offset vertically 10 mm to avoid a short.
"""
from pathlib import Path
import os, json, subprocess, tempfile, re, math
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
NEC=os.environ.get('NEC2C','/tmp/metantenna-nec2c/nec2c')

def deck(length=1.,angle=45.,height=1.,frequencies=(32.55,),segments=31,soil=(13.,.005),pattern=True,free=False,sep=.01):
    a=np.deg2rad(angle);d=length*np.cos(a);drop=length*np.sin(a)
    if height-drop<.15:raise ValueError('wire tips less than 0.15 m above ground')
    lines=['CM Crossed inverted V; copper; X excited; Y 50 ohm termination','CE']
    def wire(tag,n,p,q):lines.append('GW %d %d '%(tag,n)+' '.join(f'{v:.8g}' for v in [*p,*q,.001]))
    wire(1,3,(-.043,0,height),(.043,0,height))
    wire(2,segments,(-.043,0,height),(-.043-d,0,height-drop))
    wire(3,segments,(.043,0,height),(.043+d,0,height-drop))
    wire(4,3,(0,-.043,height+sep),(0,.043,height+sep))
    wire(5,segments,(0,-.043,height+sep),(0,-.043-d,height+sep-drop))
    wire(6,segments,(0,.043,height+sep),(0,.043+d,height+sep-drop))
    lines+=['GE '+('0' if free else '1'),'GN -1' if free else f'GN 2 0 0 0 {soil[0]} {soil[1]}',
            'LD 5 0 0 0 58000000','LD 4 4 2 2 50 0','EX 0 1 2 0 1 0','PT -1']
    for f in frequencies:
        lines += [f'FR 0 1 0 0 {f:.8g} 0', 'RP 0 19 73 1000 0 0 5 5' if pattern else 'RP 0 1 1 1000 0 0 0 0']
    return '\n'.join(lines+['EN'])+'\n'

def simulate(**kwargs):
    text=deck(**kwargs)
    with tempfile.TemporaryDirectory(prefix='metantenna-nec-') as td:
        inp=Path(td)/'a.nec';out=Path(td)/'a.out';inp.write_text(text)
        subprocess.run([NEC,'-i','a.nec','-o','a.out'],cwd=td,check=True,capture_output=True,timeout=90)
        result=out.read_text()
    blocks=result.split('ANTENNA INPUT PARAMETERS')[1:];data=[]
    for block in blocks:
        header=block.split('RADIATION PATTERNS')[0]
        line=next(l for l in header.splitlines() if re.match(r'\s+1\s+2\s+[-\d.]',l))
        v=list(map(float,line.split()));z=complex(v[6],v[7])
        pattern=[]
        for l in block.split('RADIATION PATTERNS')[1].splitlines():
            try:
                vals=list(map(float,l.split()[:5]))
                if len(vals)==5:pattern.append(vals)
            except ValueError:continue
        p=np.array(pattern)
        gains=10**(p[:,4]/10)
        if kwargs.get('pattern',True):
            g=gains.reshape(73,19)
            # phi 0..360 inclusive; theta 0..90. Integral is sky coupling
            # per unit available port power, with the other port terminated.
            alpha=np.trapezoid(np.trapezoid(g*np.sin(np.deg2rad(np.arange(0,91,5))),np.deg2rad(np.arange(0,91,5)),axis=1),np.deg2rad(np.arange(0,361,5)))/(4*np.pi)
        else:alpha=np.nan
        data.append({'z':z,'zenith_dBi':float(p[0,4]),'peak_dBi':float(p[:,4].max()),'sky_fraction':float(alpha),'pattern':p})
    assert len(data)==len(kwargs.get('frequencies',(32.55,))),len(data)
    return data,text

if __name__=='__main__':
    r,_=simulate();print({k:str(v) for k,v in r[0].items() if k!='pattern'})
