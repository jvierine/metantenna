"""Build Rustplotlib figures from HDF5; provenance stays in this source."""
from pathlib import Path
import json,h5py,numpy as np
R=Path(__file__).resolve().parents[1]
s='use anyhow::Result; use rustplotlib::*; fn main()->Result<()> { let mut f=ArticleLayout::new(177.,9.)?.figure(1.,96.)?;let pp=f.grid(1,2)?;f.width_mm=177.;f.height_mm=96.;\n'
with h5py.File(R/'simulation/end_to_end.h5') as h,h5py.File(R/'simulation/antenna/sky_noise.h5') as sky:
 for j in [0,1]:
  yr=[-12,20] if j==0 else [1,300]
  label='Antenna-to-receiver gain (dB)' if j==0 else 'System noise temperature (kK)'
  s+=f'f.panels[pp[{j}]].rect=Rect::new({22+j*87}.,5.,62.,63.);f.panels[pp[{j}]].axes=Some(Axes::new([30.,55.],[{yr[0]}.,{yr[1]}.],"Frequency (MHz)",{json.dumps(label)}));\n'
  if j==1:s+='f.panels[pp[1]].axes.as_mut().unwrap().set_yscale(AxisScale::Log10)?;\n'
  for name,label in [('arms_1p0m','1 m arms'),('arms_1p5m','1.5 m arms'),('arms_2p0m','2 m arms')]:
   if j==0:x=h[name]['frequency_MHz'][:];y=h[name]['available_antenna_to_rx_gain_dB'][:]
   else:x=sky['frequency_MHz'][:];y=np.median(sky[name]['system_X_K'][:],axis=1)/1000
   pts=','.join(f'[{a:.7f},{b:.7f}]' for a,b in zip(x,y))
   s+=f'f.panels[pp[{j}]].plot(vec![{pts}],{json.dumps(label)});\n'
  s+=f'f.panels[pp[{j}]].legend.as_mut().unwrap().position=LegendPosition::{"LowerRight" if j==0 else "LowerLeft"};\n'
s+='for ext in ["png","svg","pdf"] {f.save(format!("vhf/docs/end_to_end_comparison.{ext}"))?;} Ok(())}'
(R/'tools/plot/src/bin/end_to_end.rs').write_text(s)
