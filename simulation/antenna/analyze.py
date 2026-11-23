"""NEC geometry sweep and explicitly assumed receiver/noise budget.

RF active-device values are typical manufacturer figures at 100 MHz, used as
an engineering extrapolation across 30--70 MHz, not verified specifications.
"""
from pathlib import Path
import sys,json,subprocess,hashlib
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import h5py
from model import simulate,ROOT,NEC
OUT=ROOT/'simulation/antenna'
F=np.unique(np.r_[np.arange(30.,70.01,1.),32.55])

def match(z):return 4*50*z.real/abs(z+50)**2

def candidate(g):
    l,a,h=g
    r,_=simulate(length=l,angle=a,height=h,frequencies=[30,32.55,50,70],segments=31,pattern=False)
    z=np.array([q['z'] for q in r]);gain=np.array([q['zenith_dBi'] for q in r])+10*np.log10(match(z))
    return [l,a,h,*gain]

def main():
    configs=[(l,a,h) for l in np.arange(1.,2.501,.25) for a in [25.,35.,45.,55.] for h in [1.,1.5,2.,2.5,3.] if h-l*np.sin(np.deg2rad(a))>=.2]
    with ThreadPoolExecutor(max_workers=6) as pool: grid=np.array(list(pool.map(candidate,configs)))
    best=grid[np.argmax(grid[:,4])]
    near=grid[grid[:,4]>=best[4]-1]
    compact=sorted(near,key=lambda x:(x[2],-x[4]))[0]
    broad=grid[np.argmax(grid[:,3:].min(axis=1))]
    fine=np.array([candidate((l,compact[1],compact[2])) for l in np.arange(compact[0]-.2,compact[0]+.201,.025)])
    compact=fine[np.argmax(fine[:,4])]
    designs={'requested':(1.,45.,1.),'SIMONe_candidate':tuple(compact[:3]),'wideband_candidate':tuple(broad[:3]),'arms_1p5m':(1.5,25.,2.),'arms_1p0m':(1.,25.,2.),'arms_2p0m':(2.,25.,2.)}
    print('Selected geometries:',designs,flush=True)
    with h5py.File(ROOT/'simulation/validation.h5') as old:
        f0=old['frequency_MHz'][:];s21=old['s21'][:];s11=old['s11'][:]
    s=np.interp(F,f0,s21.real)+1j*np.interp(F,f0,s21.imag)
    refl=np.interp(F,f0,s11.real)+1j*np.interp(F,f0,s11.imag)
    filterloss=-20*np.log10(abs(s))
    # Assumed balun loss is 0.5 dB pending measured/vendor S-parameters.
    frontloss=.5+filterloss
    amp_gain=25.1;nf=2.7;pad=3.;coaxloss=5*np.sqrt(F/50);rxnf=6.
    lfront=10**(frontloss/10);ga=10**(amp_gain/10);lp=10**(pad/10);lc=10**(coaxloss/10)
    te_amp=290*(10**(nf/10)-1)
    te_post=(lp-1)*290/ga+lp*((lc-1)*290+lc*290*(10**(rxnf/10)-1))/ga
    te_matched=(lfront-1)*290+lfront*(te_amp+te_post)
    electronics_gain=amp_gain-frontloss-pad
    tsky=180*(F/180)**(-2.55)
    summary={}
    with h5py.File(OUT/'antenna_system.h5','w') as h5:
        h5['frequency_MHz']=F;h5['sweep_geometry_and_gains']=grid;h5['refined_SIMONe_length_sweep']=fine
        h5['filter_loss_dB']=filterloss;h5['electronics_gain_dB']=electronics_gain
        h5['sky_brightness_K']=tsky;h5['matched_receiver_temperature_K']=te_matched
        for name,(l,a,h) in designs.items():
            r,deck=simulate(length=l,angle=a,height=h,frequencies=F,segments=41)
            (OUT/f'{name}.nec').write_text(deck)
            z=np.array([q['z'] for q in r]);g=np.array([q['zenith_dBi'] for q in r]);alpha=np.array([q['sky_fraction'] for q in r]);tau=match(z)
            # Available-source transducer gain of the simulated preselector,
            # including its reflection, with a matched MMIC load. Balun is an
            # ideal matched 0.5 dB attenuator. This predicts signal transfer;
            # noise mismatch requires MMIC noise parameters not supplied here.
            gamma=(z-50)/(z+50)
            pre_gain=10**(-.5/10)*abs(s)**2*(1-abs(gamma)**2)/abs(1-10**(-.5/10)*refl*gamma)**2
            antenna_temp=alpha*tsky+(1-alpha)*290
            # First-order 50-ohm noise model: mismatch degrades receiver-referred
            # noise temperature; loss/ground pickup retained. Not a noise-wave solve.
            tsys=antenna_temp+te_matched/tau
            # Lower/higher sky and cable/receiver conditions are scenario ranges,
            # not confidence intervals. Soil sensitivity is computed separately.
            low=alpha*.5*tsky+(1-alpha)*290+te_matched/tau
            high=alpha*2*tsky+(1-alpha)*290+te_matched/tau
            d=h5.create_group(name)
            vals={'impedance_ohm':z,'power_match_50ohm':tau,'available_zenith_gain_dBi':g,
                  'peak_gain_dBi':np.array([q['peak_dBi'] for q in r]),'sky_coupling_fraction':alpha,
                  'realized_zenith_gain_dBi':g+10*np.log10(tau),
                  'signal_transfer_dB':10*np.log10(pre_gain)+amp_gain-pad,
                  'antenna_temperature_K':antenna_temp,'system_temperature_K':tsys,
                  'system_temperature_sky_low_K':low,'system_temperature_sky_high_K':high,
                  'G_over_T_dB_per_K':g-10*np.log10(tsys),
                  'pattern':np.array([q['pattern'] for q in r])}
            for k,v in vals.items():d[k]=v
            d.attrs.update(arm_length_m=l,slope_down_deg=a,feed_height_m=h,tip_height_m=h-l*np.sin(np.deg2rad(a)))
            spots={}
            for f in [30,32.55,50,70]:
                i=np.argmin(abs(F-f));spots[str(f)]={'Z_ohm':[z[i].real,z[i].imag],'zenith_gain_dBi':g[i],
                    'realized_zenith_gain_dBi':vals['realized_zenith_gain_dBi'][i],
                    'mismatch_loss_dB':-10*np.log10(tau[i]),'antenna_temperature_K':antenna_temp[i],
                    'system_temperature_K':tsys[i],'electronics_temperature_matched_K':te_matched[i],
                    'signal_transfer_dB':vals['signal_transfer_dB'][i]}
            summary[name]={'geometry':dict(d.attrs),'spots':spots}
        h5.attrs['model_limits']='Thin-wire NEC2, homogeneous soil, plastic mast, no PCB/coax common-mode model. Noise is approximate 50-ohm source model; active device extrapolated from 100 MHz.'
    checks={}
    for name,geometry in designs.items():
        rows=[]
        for seg in [21,41,61]:
            r,_=simulate(length=geometry[0],angle=geometry[1],height=geometry[2],frequencies=[32.55],segments=seg)
            q=r[0];rows.append({'segments_per_arm':seg,'R':q['z'].real,'X':q['z'].imag,'gain':q['zenith_dBi'],'sky_fraction':q['sky_fraction']})
        assert abs(rows[-1]['gain']-rows[-2]['gain'])<.1,rows
        checks[name]=rows
    # Half-wave, isolated copper dipole sanity check in free space at resonance.
    # Test separately with a straight (0 degree) very high antenna and free space.
    ref,_=simulate(length=2.14,angle=0,height=10,frequencies=[32.55],segments=41,free=True)
    assert 2.0<ref[0]['zenith_dBi']<2.3,ref[0]['zenith_dBi']
    checks['free_space_dipole_reference']={k:str(v) for k,v in ref[0].items() if k!='pattern'}
    # Soil sensitivity at the target frequency, for the practical SIMONe option.
    l,a,h=designs['SIMONe_candidate'];soil=[]
    for eps,sigma in [(5,.001),(13,.005),(20,.03)]:
        q=simulate(length=l,angle=a,height=h,frequencies=[32.55],soil=(eps,sigma),segments=41)[0][0]
        soil.append({'epsilon_r':eps,'conductivity_S_per_m':sigma,'z':[q['z'].real,q['z'].imag],
                     'zenith_gain_dBi':q['zenith_dBi'],'sky_fraction':q['sky_fraction']})
    checks['soil_sensitivity']=soil
    (OUT/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    summary['budget_assumptions']={'GALI_gain_dB_100MHz':25.1,'GALI_NF_dB_typical':2.7,
        'GALI_OIP3_dBm_100MHz':38,'GALI_OP1dB_dBm_100MHz':19.2,'balun_loss_dB_assumed':.5,
        'output_pad_dB':3,'coax_50m_loss_dB_at_50MHz_assumed':5,'receiver_NF_dB_assumed':6,
        'sky_model':'180 K * (f/180 MHz)^(-2.55); uniform upper hemisphere',
        'noise_mismatch':'50 ohm first-order approximation; MMIC noise parameters absent'}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    meta={'nec2c_source':'https://github.com/KJ7LNW/nec2c','revision':subprocess.check_output(['git','-C',str(Path(NEC).parent),'rev-parse','HEAD'],text=True).strip(),
          'binary_sha256':hashlib.sha256(Path(NEC).read_bytes()).hexdigest(),'ground':{'epsilon_r':13,'sigma_S_per_m':.005},'wire_diameter_m':.002}
    (OUT/'run_metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
