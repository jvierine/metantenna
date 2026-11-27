"""Screen independent preselector tolerance corners and the revised MMIC bias resistor."""
import concurrent.futures
import itertools
import json
from pathlib import Path

import numpy as np

here = Path(__file__).resolve().parent
model = here.parent / "vhf-low-cost" / "spice_tolerance.py"
source = model.read_text().split("rng=np.random.default_rng")[0]
source = source.replace(
    "l*1e-9/q:.12g", 'l*1e-9/q[{"lh":0,"l2":1,"l4":2}[n]]:.12g'
).replace(
    "cp=[.1,.1,.1] if variant=='original' else",
    "cp=[.1, 1e12/((2*np.pi*1250e6)**2*100e-9), .1] if variant=='mixed' else",
)
ns = {"__file__": str(model)}
exec(source, ns)
values = ns["VALUES"]
frequency = ns["F"]
in_band = (frequency >= 30) & (frequency <= 55)
fm = (frequency >= 88) & (frequency <= 108)
tolerance = np.array([.05,.02,.05,.05,.05,.05,.05,.02,.05,.05,.05])

def screen(job):
    s = ns["run"](job)
    gain = 20*np.log10(abs(s[:,1,0]))
    return gain[in_band].min(), gain[in_band].max()-gain[in_band].min(), gain[in_band].max()-gain[fm].max()

jobs = [
    ("mixed", values*(1+np.array(signs)*tolerance), [70, q, 70])
    for signs in itertools.product((-1,1), repeat=len(values))
    for q in [35]
]
# One fixed-Q corner screen. Q at 50 MHz is assumed, not measured.
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    corners=np.array(list(pool.map(screen,jobs)))
bias=[]
for t, amp, rtol, vtol in itertools.product([-50,25,30],[4.3,4.8,5.3],[.95,1.05],[.98,1.02]):
    r=43*rtol
    i=(1.194*6.76*vtol-(amp-.0031*(t-25)))/(r+1.8)
    bias.append((i, i*i*r))
bias=np.array(bias)
assert bias[:,0].max()<.12 and bias[:,1].max()<.5
result={
    "scope":"Linear 50-ohm filter, assumed Q 70/35/70 at 50 MHz. Bias bounds extrapolated to -50 C; not hardware qualification.",
    "filter_corners":len(jobs),
    "worst_30_55_transmission_dB":float(corners[:,0].min()),
    "max_30_55_ripple_dB":float(corners[:,1].max()),
    "min_FM_rejection_relative_to_passband_dB":float(corners[:,2].min()),
    "bias_current_mA_range":(1000*np.array([bias[:,0].min(),bias[:,0].max()])).tolist(),
    "max_bias_resistor_W":float(bias[:,1].max()),
}
(here/"docs/local_parts_screen.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
