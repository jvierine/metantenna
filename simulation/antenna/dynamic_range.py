"""First-order, typical-value dynamic-range budget; no nonlinear RF simulation.

Manufacturer GALI-74+ typical gain/OIP3/OP1dB are quoted at 100 MHz. Using
these at 32.55 MHz is an extrapolation requiring two-tone/compression tests.
"""
import json
import numpy as np
import h5py
from model import ROOT

with h5py.File(ROOT/'simulation/antenna/antenna_system.h5') as h:
    f=h['frequency_MHz'][:];i=np.argmin(abs(f-32.55));d=h['SIMONe_candidate']
    gain=float(d['signal_transfer_dB'][i])
    with h5py.File(ROOT/'simulation/antenna/sky_noise.h5') as sky:
        temp=float(np.median(sky['SIMONe_candidate/system_X_K'][i]))
    prematch_gain=gain-25.1+3
    iip3=38-25.1-prematch_gain
    ip1=19.2-25.1-prematch_gain
    n0=10*np.log10(1.380649e-23*temp*1000)
    sfdr=(2/3)*(iip3-n0)
    rows={}
    for bw in [1,1000,100000,1000000]:
        noise=n0+10*np.log10(bw)
        rows[str(bw)]={'noise_dBm':float(noise),'compression_to_noise_dB':float(ip1-noise),
                       'two_tone_SFDR_dB':float(sfdr-(2/3)*10*np.log10(bw))}
    result={'status':'Budget extrapolated from 100 MHz manufacturer typical values; NOT measured 30-55 MHz specifications',
            'reference':'antenna available-power input; selected geometry at 32.55 MHz',
            'head_output_reference':'antenna-head SMA, before coax; 3 dB output pad',
            'head_gain_dB':gain,'input_IP3_dBm':float(iip3),'input_1dB_compression_dBm':float(ip1),
            'head_output_IP3_dBm':35.,'head_output_1dB_compression_dBm':16.2,
            'noise_density_dBm_per_Hz':float(n0),'SFDR_dB_Hz_2over3':float(sfdr),
            'system_temperature_K':temp,'bandwidth_Hz':rows,
            'limits':'Single amplifier bottleneck assumed; balun/filter linearity, blocker desensitization, pulse recovery, receiver ADC headroom and actual MMIC noise mismatch are unverified.'}
(ROOT/'simulation/antenna/dynamic_range.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
