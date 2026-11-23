# Engineering model and reproduction

## Status and reference planes

This is a receiver prototype. NEC2 predicts thin-wire antenna impedance and
patterns; ngspice predicts the passive preselector; amplifier and noise budgets
use explicit assumptions. There is no measured complete-system gain, noise
figure, IP3, compression, cross-polarization isolation, pulse recovery or
weather qualification. Manufacturing archives remain prototypes.

Antenna gain is per linear polarization, with the other port terminated in
50 ohms. Realized gain includes mismatch to 50 ohms. It excludes amplifier gain.
Signal power gain is antenna available power to antenna-head SMA output,
including the approximate balun, filter, amplifier and 3 dB pad. It excludes
coax attenuation. Noise temperature is referred to antenna available power and
includes the assumed 50 m coax and receiver. A circularly polarized incident
signal incurs 3 dB polarization loss in one linear channel; calibrated X/Y
combining can recover the polarized signal.

## Geometry, solver and checks

The model uses four 2 mm diameter bare copper arms, an 86 mm central feed span,
a plastic mast, and homogeneous Sommerfeld/Norton ground with relative
permittivity 13 and conductivity 0.005 S/m. Angles are downward from horizontal.
Feed height is measured from ground to the PCB terminal plane. Each arm length
excludes the board feed span. Y's idealized central bridge is 10 mm above X to
avoid electrically joining the orthogonal ports. Y is terminated in 50 ohms.
The actual PCB, mast dielectric, enclosure, coax shield currents, ropes, nearby
objects, array coupling and insulation are absent. A common-mode choke and the
installed feed arrangement require separate evaluation.

The requested baseline is 1 m arms, 45 degrees, 1 m feed height; tips are
0.293 m above ground. At 32.55 MHz it gives about 7.4 - j792 ohms. The present
50-ohm front end therefore loses about 26 dB through mismatch. The passive
filter's good 50-ohm transmission cannot establish antenna-system sensitivity.

The coarse sweep spans 1--2.5 m arm length, 25/35/45/55 degrees, and 1--3 m
feed height, rejecting tips below 0.2 m. The compact candidate is selected
within 1 dB of the sweep's best 32.55 MHz realized zenith gain, favouring a
shorter mast; arm length is then refined in 25 mm increments at its chosen
angle and height. This is a constrained grid search, not proof of a global
optimum. The resulting 2.15 m / 25 degree / 2 m candidate has 1.091 m tip height
and 3.983 m horizontal tip-to-tip span. Its match becomes poor toward 50--70 MHz.
The separately stored wideband sweep candidate optimizes only four sampled
frequencies and should not be described as a broadband optimum.

Arm segmentation of 21, 41 and 61 segments is compared at 32.55 MHz. Between
41 and 61 segments the selected candidate's zenith gain changes by less than
0.03 dB. An isolated straight dipole sanity case gives 2.11 dBi. These are
numerical checks, not physical validation. Dry/average/wet soil scenarios
(5, 0.001), (13, 0.005), (20, 0.03) give approximately 3.9--5.7 dBi zenith gain
for the selected geometry. Soil and installation can matter more than the
remaining segmentation error. Full sweeps and patterns are in HDF5.

## Noise budget

Current plots use **PyGDSM GlobalSkyModel16 (GSM2016)** in Rayleigh-Jeans
kelvin, with CMB included. The model is convolved with the NEC receive power
pattern at each frequency, rather than using a single all-sky temperature.
The reference latitude is 54.12 degrees north; X is east-west and the nominal
Y beam is the X beam rotated by 90 degrees. Local sidereal time is sampled
at half-hour intervals through a full day. Longitude only changes the UTC
mapping of that sidereal day. This is a representative German deployment,
not a specified receiver location or observation date.

The GSM Galactic pixel directions are transformed to equatorial and then
local east/north/up coordinates. Only above-horizon pixels contribute. The
single-polarization sky contribution is sum(G * T_sky * dOmega)/(4 pi).
The HEALPix integration uses NSIDE 32 after generating NSIDE 64 GSM maps;
a comparison at NSIDE 64 differs by less than 0.01% at 32.55 MHz. The smooth
5-degree NEC beam grid, ground model and sky-model uncertainties remain more
important limitations. The tiny numerical beam normalization difference is
rescaled to the independent NEC upper-hemisphere power-gain integral.

The upper-hemisphere NEC gain integral divided by 4 pi gives alpha. Remaining
coupling is treated as a 290 K ground, conductor or terminated-port contribution:
T_ground/loss = (1-alpha) 290 K. The sky contribution is not divided by alpha,
because the model includes real ground/structure losses. GSM maps are unpolarized;
there is no extra factor of two for one linear receiver channel.

Assumed hardware values: 0.5 dB balun loss, simulated filter loss, 25.1 dB
amplifier gain, 2.7 dB amplifier NF, 3 dB output pad, 5 dB coax loss at 50 MHz
scaling as sqrt(f), and 6 dB following-receiver NF. Components are at 290 K.
The coax model is a scenario, not a specified cable product. The selected
nearly matched antenna gives approximately 384 K receiver contribution at
32.55 MHz, about 122 K ground/loss, and 7,660--12,620 K X-port sky contribution.
The total X-port result is about 8,160--13,130 K over the sidereal day, with
10,010 K median. The Y-port approximation is stored separately. Sun, man-made
noise, RFI, ionospheric absorption/emission, terrain and nearby structures
are excluded. These temperatures are model outputs, not installed measurements.

Friis noise propagation is followed by the first-order mismatch model
T_sys = T_sky_contribution + T_ground/loss + T_receiver_matched / tau,
where tau = 4 * 50 * Re(Z_ant) / |Z_ant + 50|^2. This is an uncorrelated
50-ohm noise approximation. GALI noise parameters F_min, R_n and Gamma_opt
are unavailable; filter mismatch and amplifier noise correlations are not
solved. The badly mismatched 1 m configuration's ~160,000 K is therefore
an order-of-magnitude indicator, not a calibrated prediction. The original
uniform power-law sky comparison remains in antenna_system.h5; current public
noise plots and dynamic-range numbers use sky_noise.h5 instead.

The signal-transfer curve uses complex preselector S11/S21, antenna source
reflection, an ideal matched 0.5 dB balun attenuator, and assumed amplifier
gain. This is more detailed than the noise mismatch approximation and does
not establish complete-system noise figure under severe mismatch.

## Dynamic range

Mini-Circuits quotes typical GALI-74+ values at 100 MHz of 25.1 dB gain,
+38 dBm output IP3 and +19.2 dBm output 1 dB compression, with 2.7 dB typical
NF. The budget extrapolates these to 32.55 MHz. They are not guaranteed
30--70 MHz specifications and are not the result of nonlinear simulation.
The 3 dB output pad yields estimated head-SMA OIP3 +35 dBm and OP1dB +16.2 dBm.
With the selected geometry the estimated input-referred values are +13.7 dBm
IIP3 and -5.1 dBm IP1dB, with ~21.2 dB head gain.

For the illustrative 10,000 K background, kT is -158.6 dBm/Hz. Two-tone SFDR
is (2/3)(IIP3 - noise density), about 115 dB Hz^(2/3), or 95 dB in 1 kHz,
82 dB in 100 kHz and 75 dB in 1 MHz. These are equal-tone, unity-SNR budget
values. They are not ADC dynamic-range specifications. Balun nonlinearity,
filter voltage handling, strong out-of-band blockers, pulse recovery and the
following receiver can set tighter limits. The passive wire antenna itself
has no meaningful amplifier-style IP3 specification.

## Passive filter limits

The current design targets 30--55 MHz, with nominal FM attenuation above
45 dB and 42.5 dB in the worst of 300 Q=70 tolerance trials. Maximum passband
loss is 0.38 dB nominally and 0.41 dB in those trials. Fixed-Q scenarios of
20, 40 and 70 give approximately 1.14, 0.61 and 0.38 dB maximum passband loss;
nominal FM rejection stays above 45 dB in these scenarios. Q uncertainty was
not combined with the component-tolerance trials. Standard 0805HP 100/120/220 nH
parts are used; 240 nH, absent from the selected manufacturer series, is avoided.


The plotted filter transmission covers 0--150 MHz. DC transmission is zero
because of series capacitors (minus infinity dB, below the plotted floor).
The AC sweep begins at 1 MHz. The original passband result assumes 50-ohm
ports, finite inductor Q of 70 at 50 MHz, C0G capacitor ESR/ESL and simple pad
parasitics. The 300-trial tolerance sweep uses independent uniform +/-2%
inductors and +/-1% capacitors; it is not exhaustive worst-case analysis.
PCB coupling and distributed parasitics have not been electromagnetically
extracted. The two upper-stopband zeros suppress FM; rejection rises again
above that stopband, as the 150 MHz plot makes visible.

## Reproduce

Use base conda Python with numpy, scipy, h5py, shapely, openpyxl, Pillow,
manifold3d, trimesh, pygdsm and healpy. Use ngspice and a compiled nec2c binary. The exact
solver source revision and binary hash are in the run metadata. The helper
below builds the pinned external solver without vendoring its source.

```sh
sh tools/install_nec2c.sh /tmp/metantenna-nec2c
export NEC2C=/tmp/metantenna-nec2c/nec2c
conda run -n base python simulation/validate.py
conda run -n base python simulation/antenna/analyze.py
conda run -n base python simulation/antenna/sky_noise.py
conda run -n base python simulation/antenna/dynamic_range.py
conda run -n base python simulation/antenna/plot.py
conda run -n base python simulation/prepare_plot.py
cargo run --release --manifest-path tools/plot/Cargo.toml --bin antenna
cargo run --release --manifest-path tools/plot/Cargo.toml --bin metantenna-plots
conda run -n base python mechanical/deployment_drawing.py
conda run -n base python hardware/build.py
conda run -n base python hardware/schematic.py
conda run -n base python hardware/check_layout.py
conda run -n base python hardware/check_feeds.py
conda run -n base python hardware/export_fab.py
```

Plotting uses the sibling Rustplotlib checkout. SVG deployment drawings can
be exported to PNG/PDF with Inkscape. HDF5 stores scientific arrays; XLSX stores
assembly tables. Native KiCad CI fills planes and exports CAD previews and
fabrication files. A successful export is not certification that all reported
DRC/library/parity warnings have been resolved. Read the actual reports.

## Sources

- [NEC2 user's guide](https://www.nec2.org/part_3/toc.html)
- [nec2c source](https://github.com/KJ7LNW/nec2c)
- [GALI-74+ manufacturer datasheet](https://www.minicircuits.com/pdfs/GALI-74.pdf)
- [Manufacturer typical performance](https://www.minicircuits.com/pages/s-params/GALI-74%2B_VIEW.pdf)
- [Example sky-temperature power law used in PAPER](https://openaccess.inaf.it/bitstream/20.500.12386/29067/1/Kolopanis19.pdf)
- [SIMONe meteor-radar system](https://amt.copernicus.org/articles/14/7199/2021/)

- [PyGDSM implementation and references](https://github.com/telegraphic/pygdsm)
- [GSM2016 sky-model paper](https://ui.adsabs.harvard.edu/abs/2017MNRAS.464.3486Z/abstract)

## Bias-tee input filter

CM1 is TDK ACM7060-701-2PL-TL01 (LCSC C78246), two windings 1–4 and
2–3, 700 ohm typical common-mode impedance at 100 MHz, 4 A rating and
15 milliohm maximum per line at 20 C. The unfiltered supply return is a
separate net and has no plane connection until CM1 pin 3. The four ground
pours omit x=34…50 mm, y=0…14 mm under the dirty input pair; RF reference
planes remain continuous under both coax signal paths.

FB1 is Murata BLM21PG601SN1D (600 ohm at 100 MHz, 1.4 A, 0.14 ohm max).
C1 is the upstream bulk bypass. C2/C3 provide downstream 1 nF / 100 nF
bypassing, and R1/C4 form a 1 ohm / 10 uF series shunt for damping. R1 is
not in the DC supply path. Existing C11 remains local to the bias feed.
The choke and bead add 0.17 ohm maximum at 20 C to the DC loop.

References: [TDK dimensions, pins and ratings](https://product.tdk.com/system/files/dam/doc/product/emc/emc/cmf_cmc/catalog/cmf_commercial_power_acm7060_en.pdf),
[Murata ferrite ratings](https://www.murata.com/-/media/webrenewal/tool/library/common-pdf/static-model/component-list-fb-s-2602.ashx?cvid=20260515010000000000&la=en-sg).

The differential SPICE screening uses approximate lumped ferrite/leakage
models, capacitor ESL/ESR and reduced effective bulk capacitance (3 uF).
It checks source resistance and inductance sensitivity, not PCB radiated
coupling or common-mode insertion loss. Its very small RF transfers must
not be advertised as physical shielding or rejection specifications.
A supply-to-coax injection measurement and stability check are required.


## Factory-mounted coax common-mode barriers

CM10 and CM20 are TDK ACM4520-901-2P-T000, JLC C41519. The catalogue
lists about $1.07 each at unit quantity; this is a component indication,
not an assembled quote. SMA 132203 is JLC C6784103. All are included in
the full-assembly BOM/CPL. No wound harness or added bulkhead is used.

On each port, pins 1–4 carry the centre conductor and pins 2–3 the shield
return. Antenna-facing shields have separate four-layer copper islands;
no metal enclosure plate, mounting strap or ground pour may bridge them to
indoor ground. C21 is a 1 nF C0G series DC block in the Y shield return.
Without it, the shared antenna-head ground would split the supply return
between X and Y and unbalance the chokes. This PCB is not a protective-earth
or lightning-current path.

The screening model uses TDK's published ACM4520 equivalent circuit, with
coupling decreased to 0.99 and outer parasitics increased 50% as sensitivity
cases. Nominal 30–55 MHz loss is <=0.443 dB; tested cases <=0.958 dB.
Those cases are not manufacturing tolerances or a guarantee. Common-mode
fixture attenuation depends on source/load impedances and is not an antenna
site rejection specification. PCB parasitic bypass and nonlinear behavior
still require bench tests. This choke is not a low-frequency HF solution.

[TDK ratings and land pattern](https://product.tdk.com/system/files/dam/doc/product/emc/emc/cmf_cmc/catalog/cmf_commercial_power_acm4520_en.pdf),
[TDK equivalent circuit](https://product.tdk.com/system/files/dam/technicalsupport/tvcl/pdf/cmf_commercial_power_acm4520_ecm.pdf),
[JLC component](https://jlcpcb.com/partdetail/TDK-ACM4520_901_2Pt000/C41519).

The X RF-port choke adds a further 0.12 ohm maximum loop resistance
(two 0.06 ohm windings); the full added filter resistance is 0.29 ohm.


## HF CLF9060-202Y development selection and SPICE screening

The HF usable-band target is now 0.1–30 MHz, with nominal 100 kHz high-pass
and 30 MHz low-pass targets. The Linekey CLF9060-202Y (JLC C2941480) is
selected for low-frequency development on each polarization. This is not an
HF PCB fabrication release. Its manufacturer data give 2 mH +/-50%, 0.42 ohm
maximum DCR, 0.6 A, and >=3 kohm common-mode impedance over 1–5 MHz. The
manufacturer measuring fixture connects the two windings in parallel.

Approximate manually read points from the 202Y magnitude graph are stored in
HDF5. Two series parallel-RLC branches fit those points with <=8.9% relative
error. This is a passive, nonunique magnitude-only model, not a vendor model.
Its common-mode low-frequency equivalent inductance is about 1.19 mH, within
the listed +/-50% range. A paired-winding SPICE implementation reproduces the
fit. Pin pairs are 1–4 and 2–3; body and land dimensions are retained in the HF
development definition. The source PDF hash identifies the datasheet used.

Ngspice screening covers 180 assumption combinations of inductance, coupling,
self-capacitance scaling and inter-winding capacitance, with 50-ohm DM and CM
fixtures. All screened networks retain >=3 kohm CM impedance in the specified
1–5 MHz interval. The common-mode curve cannot determine coupling/leakage:
for the fitted branch model and assumed 5 pF inter-winding capacitance,
k=0.99999,0.9999,0.999 give about0.07,0.80,14.24 dB loss at30MHz. An ideal
k=1 run conceals the RF loss. Counts of cases passing arbitrary screening
limits are not probabilities, tolerances, or manufacturing yield estimates.
The model says nothing about magnetic nonlinearities or amplifier IP3.

The 0.42 ohm per-winding resistance assumption adds0.84 ohm to the X DC loop
(0.16 V at191mA as a reference example, not the unspecified HF amplifier's
actual current). The full HF power budget and DC-return isolation still need
the final amplifier circuit. Vendor differential data or bench S-parameters
are required to qualify wanted-signal transmission; common-mode magnitude
alone cannot establish that the stage works across0.1–30MHz.
