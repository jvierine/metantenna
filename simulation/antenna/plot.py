"""Generate Rustplotlib source from the HDF5 antenna/system calculation."""
from pathlib import Path
import json
import h5py
import numpy as np
from model import ROOT

s='''// Scientific plotting source generated from antenna_system.h5.
use anyhow::Result;
use rustplotlib::*;
fn main()->Result<()> {
let mut f=ArticleLayout::new(177.,9.)?.figure(1.,156.)?;
let pp=f.grid(2,2)?;
f.width_mm=177.; f.height_mm=156.;
'''

def panel(j,xr,yr,ylabel,curves,log=False):
    global s
    x=19+(j%2)*87;y=5+(j//2)*76
    s+=f'f.panels[pp[{j}]].rect=Rect::new({x}.,{y}.,65.,54.);\n'
    s+=f'f.panels[pp[{j}]].axes=Some(Axes::new([{xr[0]:.4f},{xr[1]:.4f}],[{yr[0]:.6f},{yr[1]:.6f}],"Frequency (MHz)",{json.dumps(ylabel)}));\n'
    if log:s+=f'f.panels[pp[{j}]].axes.as_mut().unwrap().set_yscale(AxisScale::Log10)?;\n'
    for label,x,y in curves:
        points=','.join(f'[{xx:.8f},{yy:.8f}]' for xx,yy in zip(x,y))
        s+=f'f.panels[pp[{j}]].plot(vec![{points}],{json.dumps(label)});\n'
    if len(curves)>1:s+=f'f.panels[pp[{j}]].legend.as_mut().unwrap().position=LegendPosition::'+('UpperRight' if log else 'LowerLeft')+';\n'
    else:s+=f'f.panels[pp[{j}]].legend=None;\n'

with h5py.File(ROOT/'simulation/antenna/antenna_system.h5') as h:
    f=h['frequency_MHz'][:]
    short=h['requested'];long=h['SIMONe_candidate'];l=long.attrs['arm_length_m']
    labels=['1 m arms',f'{l:.3g} m arms']
    with h5py.File(ROOT/'simulation/validation.h5') as hf:
        ff=hf['frequency_MHz'][:]; ss=hf['s21'][:]; sel=ff<=150
        fx=np.r_[0.,ff[sel]]; fy=np.r_[-100.,20*np.log10(abs(ss[sel]))]
    panel(0,[0,150],[-80,2],'Filter transmission (dB)',[('50 ohm',fx,fy)])
    panel(1,[30,55],[-30,8],'Realized zenith gain (dBi)',[(labels[0],f,short['realized_zenith_gain_dBi'][:]),(labels[1],f,long['realized_zenith_gain_dBi'][:])])
    panel(2,[30,55],[-10,25],'Signal power gain (dB)',[(labels[0],f,short['signal_transfer_dB'][:]),(labels[1],f,long['signal_transfer_dB'][:]),('50 ohm electronics',f,h['electronics_gain_dB'][:])])
    with h5py.File(ROOT/'simulation/antenna/sky_noise.h5') as sk:
        short_t=np.median(sk['requested/system_X_K'][:],axis=1)
        long_t=np.median(sk['SIMONe_candidate/system_X_K'][:],axis=1)
        sky_t=np.median(sk['SIMONe_candidate/sky_X_K'][:],axis=1)
        panel(3,[30,55],[300,300000],'System temperature (K)',[(labels[0],f,short_t),(labels[1],f,long_t),('Sky (PyGDSM)',f,sky_t)],True)
s+='eprintln!("Response figure"); for ext in ["png","pdf","svg"] {f.save(format!("vhf/docs/antenna_system_response.{ext}"))?;}\n'
s+='''let mut g=ArticleLayout::new(177.,10.)?.figure(1.,88.)?;
let qq=g.grid(1,2)?;g.width_mm=177.;g.height_mm=88.;
'''
with h5py.File(ROOT/'simulation/antenna/antenna_system.h5') as h:
    for j,name in enumerate(['requested','SIMONe_candidate']):
        d=h[name];idx=np.argmin(abs(h['frequency_MHz'][:]-32.55));p=d['pattern'][idx].reshape(73,19,5);loss=10*np.log10(d['power_match_50ohm'][idx])
        s+=f'g.panels[qq[{j}]].rect=Rect::new({19+j*87}.,5.,65.,58.);\n'
        s+=f'g.panels[qq[{j}]].axes=Some(Axes::new([0.,90.],[-35.,8.],"Elevation (deg)","Realized gain at 32.55 MHz (dBi)"));\n'
        for label,k in [('Along X',0),('Across X',18)]:
            pts=','.join(f'[{90-v[0]:.8f},{max(-100,v[4]+loss):.8f}]' for v in p[k])
            s+=f'g.panels[qq[{j}]].plot(vec![{pts}],"{label}");\n'
        s+=f'g.panels[qq[{j}]].legend.as_mut().unwrap().position=LegendPosition::LowerRight;\n'
s+='eprintln!("Pattern figure"); for ext in ["png","pdf","svg"] {g.save(format!("vhf/docs/antenna_patterns.{ext}"))?;}\n'
s+="""let mut n=ArticleLayout::new(177.,9.)?.figure(1.,92.)?;
let nn=n.grid(1,2)?;n.width_mm=177.;n.height_mm=92.;
"""
with h5py.File(ROOT/'simulation/antenna/sky_noise.h5') as sk:
    ff=sk['frequency_MHz'][:];tt=sk['local_sidereal_time_hours'][:];d=sk['SIMONe_candidate'];i=np.argmin(abs(ff-32.55))
    curves=[[
        ('Total',ff,np.median(d['system_X_K'][:],axis=1)),
        ('Sky',ff,np.median(d['sky_X_K'][:],axis=1)),
        ('Receiver',ff,d['receiver_equivalent_K'][:]),
        ('Ground / loss',ff,d['ground_and_loss_K'][:])],
        [('Total X',tt,d['system_X_K'][i]),('Total Y',tt,d['system_Y_K'][i]),('Sky X',tt,d['sky_X_K'][i])]]
    for j in range(2):
        s+=f'n.panels[nn[{j}]].rect=Rect::new({27+j*85}.,5.,58.,60.);\n'
        xlabel='Frequency (MHz)' if j==0 else 'Local sidereal time (h)'
        xr=[30.,55.] if j==0 else [0.,24.];yr=[.05,50.] if j==0 else [0.,15.]
        s+=f'n.panels[nn[{j}]].axes=Some(Axes::new([{xr[0]},{xr[1]}],[{yr[0]},{yr[1]}],{json.dumps(xlabel)},"Noise temperature (kK)"));\n'
        if j==0:s+=f'n.panels[nn[{j}]].axes.as_mut().unwrap().set_yscale(AxisScale::Log10)?;\n'
        for label,x,y in curves[j]:
            if j==1:x=np.r_[x,24.];y=np.r_[y,y[0]]
            pts=','.join(f'[{xx:.8f},{yy:.8f}]' for xx,yy in zip(x,np.asarray(y)/1000))
            s+=f'n.panels[nn[{j}]].plot(vec![{pts}],{json.dumps(label)});\n'
        s+=f'n.panels[nn[{j}]].legend.as_mut().unwrap().position=LegendPosition::LowerLeft;\n'
s+='eprintln!("Noise figure"); for ext in ["png","pdf","svg"] {n.save(format!("vhf/docs/sky_noise_budget.{ext}"))?;} Ok(())}\n'
p=ROOT/'tools/plot/src/bin';p.mkdir(exist_ok=True);(p/'antenna.rs').write_text(s)
