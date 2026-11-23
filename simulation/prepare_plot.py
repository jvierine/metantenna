"""Read the HDF5 results and generate Rustplotlib plotting source."""
from pathlib import Path
import h5py
import numpy as np
R=Path(__file__).resolve().parents[1]
with h5py.File(R/'simulation/validation.h5') as h:
    f=h['frequency_MHz'][:]; nominal=20*np.log10(abs(h['s21'][:])); mc=h['monte_carlo_s21_dB'][:]
    curves=[nominal,mc.min(axis=0),mc.max(axis=0)]
source='''// Generated from simulation/validation.h5; scientific provenance only.
use anyhow::Result;
use rustplotlib::*;
fn main()->Result<()> {
let mut f=ArticleLayout::new(177.,10.)?.figure(1.,90.)?;
let pp=f.grid(1,2)?;
f.width_mm=177.; f.height_mm=90.;
'''
for j,(xrange,yrange) in enumerate([([30,55],[-1.3,0.1]),([0,150],[-80,2])]):
    source+=f'f.panels[pp[{j}]].rect=Rect::new({18+j*87}.,6.,66.,65.);\n'
    source+=f'f.panels[pp[{j}]].axes=Some(Axes::new([{xrange[0]}.,{xrange[1]}.],[{yrange[0]:.1f},{yrange[1]:.1f}],"Frequency (MHz)","Transmission (dB)"));\n'
    for label,y in zip(['Nominal','Tolerance minimum','Tolerance maximum'],curves):
        idx=np.flatnonzero((f>=xrange[0])&(f<=xrange[1]))[::4]
        pts=','.join(f'[{f[i]:.8f},{y[i]:.8f}]' for i in idx)
        source+=f'f.panels[pp[{j}]].plot(vec![{pts}],"{label}");\n'
    source+=f'f.panels[pp[{j}]].legend.as_mut().unwrap().position=LegendPosition::LowerLeft;\n' if j==0 else f'f.panels[pp[{j}]].legend=None;\n'
source+='for ext in ["svg","png","pdf"] { f.save(format!("docs/filter_response.{ext}"))?; } Ok(()) }\n'
p=R/'tools/plot/src';p.mkdir(parents=True,exist_ok=True);(p/'main.rs').write_text(source)
