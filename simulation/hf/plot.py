"""Rustplotlib output of the HF screening model; no measured-noise claim."""
from pathlib import Path
import numpy as np,h5py
R=Path(__file__).resolve().parents[2]
with h5py.File(R/'simulation/hf/screening.h5') as h:
 f=h['frequency_Hz'][:]/1e6;m=(f>=.1)&(f<=30);f=f[m]
 g=20*np.log10(abs(h['voltage_gain'][:][m]));n=h['input_voltage_noise_V_per_sqrtHz'][:][m]*1e9
 def vec(v):return 'vec!['+','.join('[%.9f,%.9f]'%(x,y) for x,y in zip(f,v))+']'
 code='''use anyhow::Result;use rustplotlib::*;fn main()->Result<()> {
 let mut f=ArticleLayout::new(177.,11.)?.figure(1.,91.)?;let pp=f.grid(1,2)?;f.width_mm=177.;f.height_mm=91.;
 f.panels[pp[0]].rect=Rect::new(22.,5.,63.,62.);f.panels[pp[1]].rect=Rect::new(109.,5.,63.,62.);
 f.panels[pp[0]].axes=Some(Axes::new([0.1,30.],[0.,20.],"Frequency (MHz)","Voltage gain (dB)"));
 f.panels[pp[1]].axes=Some(Axes::new([0.1,30.],[0.,8.],"Frequency (MHz)","Input noise (nV/$\\\\sqrt{\\\\rm Hz}$)"));
 for p in &pp {f.panels[*p].axes.as_mut().unwrap().set_xscale(AxisScale::Log10)?;}
 '''
 for i,v in enumerate([g,n]):code+=f'f.panels[pp[{i}]].push(Layer::Line(Line::series({vec(v)},0)));\n'
 code+='for ext in ["png","pdf","svg"] {f.save(format!("hf/docs/hf_frontend_screening.{}",ext))?;}Ok(())}'
 (R/'tools/plot/src/bin/hf_frontend.rs').write_text(code)
