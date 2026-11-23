"""Convolve NEC receive power patterns with PyGDSM GSM2016 over sidereal time.

Radiometric convention: an unpolarized sky with Rayleigh-Jeans brightness T
contributes integral(G*T*dOmega)/(4*pi) to one linear receiver port. Ground
and internal losses contribute separately at 290 K. X is east-west, Y north-
south; the Y beam is the nominal 90-degree rotation of the X NEC beam.
"""
import json,hashlib,importlib.metadata
import numpy as np
import h5py,healpy as hp
from scipy.interpolate import RegularGridInterpolator
from pygdsm import GlobalSkyModel16
from model import ROOT

LAT=54.12
LST=np.arange(0,24,.5)
NSIDE=32

def directions(nside):
    pix=np.arange(hp.nside2npix(nside));t,p=hp.pix2ang(nside,pix)
    # GSM2016 maps are Galactic. Rotate pixel directions to equatorial.
    te,ra=hp.Rotator(coord=['G','C'])(t,p);dec=np.pi/2-te
    ha=np.deg2rad(15*LST[:,None])-ra[None,:];lat=np.deg2rad(LAT)
    up=np.sin(lat)*np.sin(dec)[None,:]+np.cos(lat)*np.cos(dec)[None,:]*np.cos(ha)
    east=-np.cos(dec)[None,:]*np.sin(ha)
    north=np.cos(lat)*np.sin(dec)[None,:]-np.sin(lat)*np.cos(dec)[None,:]*np.cos(ha)
    theta=np.rad2deg(np.arccos(np.clip(up,-1,1)))
    phi=np.rad2deg(np.arctan2(north,east))%360
    return theta,phi,up>0

def convolve(pattern,sky,nside,rotation=0):
    theta,phi,visible=directions(nside)
    p=pattern.reshape(73,19,5)
    g=10**(p[:,:,4]/10)
    fun=RegularGridInterpolator((np.arange(0,361,5),np.arange(0,91,5)),g,bounds_error=False,fill_value=0)
    query=np.stack(((phi-rotation)%360,np.clip(theta,0,90)),axis=-1)
    weights=fun(query)*visible/hp.nside2npix(nside)
    return weights@sky,weights.sum(axis=1)

def main():
    gsm=GlobalSkyModel16(freq_unit='MHz',data_unit='TRJ',resolution='low',include_cmb=True)
    with h5py.File(ROOT/'simulation/antenna/antenna_system.h5') as source, h5py.File(ROOT/'simulation/antenna/sky_noise.h5','w') as out:
        f=source['frequency_MHz'][:];out['frequency_MHz']=f;out['local_sidereal_time_hours']=LST
        groups={name:out.create_group(name) for name in ['requested','SIMONe_candidate','arms_1p5m','arms_1p0m','arms_2p0m']}
        stats={}
        for name,d in groups.items():
            pattern=source[name]['pattern'][:];alpha=source[name]['sky_coupling_fraction'][:]
            tau=source[name]['power_match_50ohm'][:];rx=source['matched_receiver_temperature_K'][:]/tau
            skyx=[];skyy=[];norm=[];normy=[]
            for i,ff in enumerate(f):
                skymap=gsm.generate(float(ff));sm=hp.ud_grade(skymap,NSIDE)
                tx,n=convolve(pattern[i],sm,NSIDE);ty,ny=convolve(pattern[i],sm,NSIDE,90)
                skyx.append(tx);skyy.append(ty);norm.append(n);normy.append(ny)
            skyx=np.array(skyx);skyy=np.array(skyy);norm=np.array(norm)
            # Rescale tiny quadrature/interpolation error to the independently
            # integrated NEC beam normalization, preserving the model gain.
            skyx*=alpha[:,None]/norm;skyy*=alpha[:,None]/np.array(normy)
            ground=(1-alpha)*290
            totalx=skyx+ground[:,None]+rx[:,None];totaly=skyy+ground[:,None]+rx[:,None]
            for k,v in {'sky_X_K':skyx,'sky_Y_K':skyy,'ground_and_loss_K':ground,'receiver_equivalent_K':rx,'system_X_K':totalx,'system_Y_K':totaly}.items():
                d.create_dataset(k,data=v,compression='gzip')
            i=np.argmin(abs(f-(50. if name=='arms_1p5m' else 32.55)))
            stats[name]={'frequency_MHz':float(f[i]),'sky_X_K_min_median_max':np.percentile(skyx[i],[0,50,100]).tolist(),
                         'system_X_K_min_median_max':np.percentile(totalx[i],[0,50,100]).tolist(),
                         'system_Y_K_min_median_max':np.percentile(totaly[i],[0,50,100]).tolist(),
                         'receiver_equivalent_K':float(rx[i]),'ground_and_loss_K':float(ground[i])}
            if name=='SIMONe_candidate':
                sm64=gsm.generate(float(f[i]));v64,n64=convolve(pattern[i],sm64,64);v64*=alpha[i]/n64
                error=float(np.max(abs(v64-skyx[i])/v64));stats[name]['NSIDE32_vs64_max_relative_difference']=error
                assert error<.02,error
        out.attrs.update(model='PyGDSM GlobalSkyModel16, Rayleigh-Jeans K, CMB included',latitude_deg=LAT,
                         X_arm_azimuth_deg_from_north=90.,nside_convolution=NSIDE,
                         ground_temperature_K=290.,Y_beam='90 degree rotation of X; nominal symmetric antenna approximation',
                         excludes='Sun, RFI, ionosphere, terrain and nearby structures')
    stats['model']={'name':'PyGDSM GSM2016','version':importlib.metadata.version('pygdsm'),'latitude_deg':LAT,
                    'X_orientation':'east-west','LST_samples_hours':.5,'include_CMB':True,'data_unit':'TRJ',
                    'model_data_sha256':hashlib.sha256(open(gsm.h5.filename,'rb').read()).hexdigest()}
    (ROOT/'simulation/antenna/sky_summary.json').write_text(json.dumps(stats,indent=2)+'\n')
    print(json.dumps(stats,indent=2))
if __name__=='__main__':main()
