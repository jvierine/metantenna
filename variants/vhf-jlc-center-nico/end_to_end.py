"""Run the SURTR circuit model with PCB-derived output electrical lengths."""
from pathlib import Path
import json
import hashlib
import sys

import h5py
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'hardware'))
from check_feeds import path_length

head = json.loads((HERE / 'hardware/preamp_layout.json').read_text())
parts = {p['ref']: p for p in head['parts']}
assert all(parts[r]['value'] == '300' for r in ('R103', 'R105', 'R203', 'R205'))
assert all(parts[r]['value'] == '43 1W' for r in ('R108', 'R208'))

def pad(ref, pin):
    q = next(p for p in head['pads'] if p['ref'] == ref and p['pin'] == pin)
    return (0, round(q['x'], 4), round(q['y'], 4))

# A through-hole jack terminates the back-copper X route without a second via.
x_end = (1, parts['J102']['x'], parts['J102']['y'])
lengths_mm = {
    'X_before_tap': path_length(head, 'X_COAX', pad('C109', '2'), (0, 84.0, 20.0)),
    'X': path_length(head, 'X_COAX', pad('C109', '2'), x_end),
    'Y': path_length(head, 'Y_COAX', pad('C209', '2'), pad('J202', '1')),
    'X_bias_stub': path_length(head, 'X_COAX', (0, 84.0, 20.0), pad('L104', '1')),
}

model = HERE.parent / 'vhf-low-cost' / 'spice_tolerance.py'
spice = model.read_text().split('rng=np.random.default_rng')[0]
spice = spice.replace('l*1e-9/q:.12g', 'l*1e-9/q[{"lh":0,"l2":1,"l4":2}[n]]:.12g')
spice = spice.replace('cp=[.1,.1,.1] if', 'cp=[.1, 1e12/((2*np.pi*1250e6)**2*100e-9), .1] if')
ns = {'__file__': str(model)}
exec(spice, ns)
sweep = ns['run'](('original', ns['VALUES'], [70, 35, 70]))

source = (ROOT / 'simulation/end_to_end.py').read_text()
source = source.replace('Path(__file__).resolve().parents[1]', f'Path({str(ROOT)!r})')
for name in ('end_to_end.h5', 'end_to_end_results.json'):
    source = source.replace(f"R/'simulation/{name}'",f"Path({str(HERE / 'simulation' / name)!r})")
start = source.index(' vals=np.array(')
end = source.index(' w=2*np.pi*f*1e6', start)
source = source[:start] + '''
 f=F
 s11,s21,s12,s22=S[:,0,0],S[:,1,0],S[:,0,1],S[:,1,1]
 assert np.max(abs(s21-s12))<2e-5
''' + source[end:]
source = source.replace(" assert [P[x].value for x in ['R103','R104','R105']]==['294','18','294']\n", '')
source = source.replace('1/294','1/300')
source = source.replace('balun@pre@series(cap(coupling_cap(\'C115\')))@amp','pre@amp')
source = source.replace(' headX=pre@amp@out@shunt(1/choke);headY=pre@amp@out', '''
 def line(length_mm):
  return matched(np.exp(-1j*w*length_mm*1e-3*np.sqrt(3.2)/299792458))
 stub=line(LENGTHS['X_bias_stub'])
 zin=(stub[:,0,0]*choke+stub[:,0,1])/(stub[:,1,0]*choke+stub[:,1,1])
 headX=pre@amp@out@line(LENGTHS['X_before_tap'])@shunt(1/zin)@line(LENGTHS['X']-LENGTHS['X_before_tap']);headY=pre@amp@out@line(LENGTHS['Y'])'''.lstrip('\n'))
source = source.replace('[-20,25,60],[.99,1.01]', '[-50,25,30],[.99,1.01]')
source = source.replace('41.2*rtol','43*rtol')
source = source.replace('ambient -20..60C','ambient -50..30C DC extrapolation')
source = source.replace("'frequency_MHz':[1,100]", "'frequency_MHz':[5,150]")
source = source.replace("['system_X_K','system_Y_K','sky_X_K','sky_Y_K']", "['sky_X_K','sky_Y_K']")
source = source.replace(", 'system_X_noise_K_median':float(np.median(sky[name]['system_X_K'][j]))",'')
source = source.replace(" band=(f>=30)&(f<=55)", """
 def matched_phase_delta(x, y):
  def denominator(m):
   return m[:,0,0] + m[:,0,1]/50 + 50*m[:,1,0] + m[:,1,1]
  return np.angle(denominator(y)/denominator(x), deg=True)
 head_phase = matched_phase_delta(headX, headY)
 system_phase = matched_phase_delta(chainX, chainY)
 band=(f>=30)&(f<=55)""".lstrip("\n"))
source = source.replace("  h['filter_s11']", """
  h["head_X_minus_Y_phase_deg"] = head_phase
  h["system_X_minus_Y_phase_deg"] = system_phase
  h["filter_s11"]""".lstrip("\n"))

env = {'__file__': str(ROOT / 'simulation/end_to_end.py'), '__name__': 'surtr_model',
       'F': ns['F'], 'S': sweep, 'LENGTHS': lengths_mm}
(HERE / 'simulation').mkdir(exist_ok=True)
exec(source, env)
env['main']()

report = HERE / 'simulation/end_to_end_results.json'
summary = json.loads(report.read_text())
summary['pcb_output_lengths_mm'] = lengths_mm
summary['pcb_line_model'] = 'Lossless 50 Ω lines, effective relative permittivity 3.2. No coupling or launch field model.'
with h5py.File(HERE / 'simulation/end_to_end.h5', 'a') as h5:
    del h5.attrs['electrical_definition_sha256']
    h5.attrs['board_layout_sha256'] = json.dumps({
        name: hashlib.sha256((HERE / 'hardware' / f'{name}_layout.json').read_bytes()).hexdigest()
        for name in ('preamp', 'biastee')
    })
    frequency = h5['frequency_MHz'][:]
    band = (frequency >= 30) & (frequency <= 55)
    for scope in ('head', 'system'):
        phase = h5[f'{scope}_X_minus_Y_phase_deg'][:]
        summary[f'{scope}_X_Y_phase_difference_30_55_deg_max'] = float(np.max(np.abs(phase[band])))
    h5.attrs['summary'] = json.dumps(summary)
report.write_text(json.dumps(summary, indent=2) + '\n')
