"""Rustplotlib/LaTeX comparison figures from the actual ngspice trials."""
from pathlib import Path
import h5py,numpy as np,json
O=Path(__file__).resolve().parent;D=O/'simulation/spice_tolerance'
def vec(a):return 'vec!['+','.join(f'{float(x):.9e}' for x in a)+']'
def points(x,y):return 'vec!['+','.join(f'[{float(a):.9e},{float(b):.9e}]' for a,b in zip(x,y))+']'
code='use anyhow::Result;use rustplotlib::*;fn main()->Result<()>{'
with h5py.File(D/'results.h5') as h:
 code+='let mut f=ArticleLayout::new(177.,10.)?.figure(1.,88.)?;let pp=f.grid(1,2)?;f.width_mm=177.;f.height_mm=88.;'
 x=h['frequency_MHz'][:]
 for j,xlim,ylim in [(0,[15,80],[-8,0]),(1,[30,55],[-.95,-.15])]:
  use=(x>=xlim[0])&(x<=xlim[1]);xx=x[use][::2]
  code+=f'f.panels[pp[{j}]].rect=Rect::new({20+88*j}.,18.,65.,51.);f.panels[pp[{j}]].axes=Some(Axes::new([{xlim[0]}.,{xlim[1]}.],[{float(ylim[0])},{float(ylim[1])}],"Frequency (MHz)","Transmission (dB)"));'
  for key,label,color in [('original','Original','#0072B2'),('low_cost','Low-cost','#D55E00')]:
   lo=h[key+'/p025_dB'][:][use][::2]+.5;hi=h[key+'/p975_dB'][:][use][::2]+.5;yy=h[key+'/median_dB'][:][use][::2]+.5
   code+=f'f.panels[pp[{j}]].uncertainty_band(&{vec(xx)},&{vec(lo)},&{vec(hi)},"{color}",0.22)?;f.panels[pp[{j}]].plot({points(xx,yy)},"{label}");'
  code+=f'f.panels[pp[{j}]].legend.as_mut().unwrap().position=LegendPosition::OutsideAboveCenter;'
 code+='for ext in ["png","pdf","svg"] {f.save(format!("variants/vhf-low-cost/docs/spice_passband.{}",ext))?;}'
 code+='let mut g=ArticleLayout::new(177.,10.)?.figure(1.,88.)?;let p=g.grid(1,1)?[0];g.width_mm=177.;g.height_mm=88.;g.panels[p].rect=Rect::new(23.,19.,143.,51.);g.panels[p].axes=Some(Axes::new([30.,55.],[-1.2,0.05],"Frequency (MHz)","Change in $G/T$ (dB)"));'
 xx=h['antenna_frequency_MHz'][:]
 for name,label,color in [('arms_1p0m','1 m arms','#0072B2'),('arms_1p5m','1.5 m arms','#D55E00'),('arms_2p0m','2 m arms','#009E73')]:
  lo,med,hi=h['comparison/'+name+'/percentiles_daily_median_change_dB'][:]
  code+=f'g.panels[p].uncertainty_band(&{vec(xx)},&{vec(lo)},&{vec(hi)},"{color}",0.2)?;g.panels[p].plot({points(xx,med)},"{label}");'
 code+='g.panels[p].legend.as_mut().unwrap().position=LegendPosition::OutsideAboveCenter;for ext in ["png","pdf","svg"] {g.save(format!("variants/vhf-low-cost/docs/spice_gt_change.{}",ext))?;}Ok(())}'
(O/'plots/src/main.rs').write_text(code)
