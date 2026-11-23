# Rev B end-to-end calculation

This is a **linear RF and DC corner simulation**, supplemented by NEC2 antenna
and PyGDSM sky calculations. It is not a transistor-level MMIC model, extracted
PCB EM simulation, or measured prototype qualification.

The cascade includes the antenna's complex source impedance, an assumed 0.5 dB
balun loss, the preselector solved by ngspice in both directions, a matched
unilateral 25.1 dB amplifier, both 1 nF output DC blocks, the actual 294/18/294 Ω
pi pad, X-side DC choke loading, 50 m of coax, and the indoor bias tee/DC block.
The coax model assumes 5 dB loss at 50 MHz, scaling as sqrt(f), and velocity
factor 0.66. X and Y are solved separately. The passive reverse solution verifies
reciprocity. Amplifier gain/NF use manufacturer typical values at 100 MHz,
extrapolated to the operating band; reverse stability and noise mismatch are not
inferred from an ideal matched stage.

## Results

- Matched 50 Ω source to receiver: X **15.92–17.28 dB**, Y **15.93–17.30 dB**,
  across 30–55 MHz including the 50 m cable.
- Modelled X/Y gain difference: **≤0.030 dB**. This is only the difference in
  modelled bias-tee loading, not a prediction of real polarization calibration.
- Passive preselector: nominal FM rejection **≥45.3 dB**; worst of 300 simultaneous
  tolerance trials **42.5 dB**. These are passive lumped-circuit results.
- 1,440 DC corners cover supply, coax loop resistance, diode drop, bias-resistor
  tolerance, regulator voltage, MMIC operating voltage and -20…60 °C ambient.
- Inside the specified installation envelope (regulated 12 V, minimum 11.76 V,
  coax loop resistance ≤3 Ω): minimum regulator input headroom is **0.58 V**,
  i.e. **0.18 V remaining after an assumed 0.40 V dropout allowance**.
- Maximum predicted total head current **191 mA**, bias resistor dissipation
  **0.367 W per channel**, regulator dissipation **0.324 W per channel**.
  Use the 1 W bias resistors. Both indoor PTCs are now 500 mA nominal hold parts;
  hot-environment hold-current derating still applies.

The sweep deliberately includes off-spec weak supplies and resistive cables;
252 of those corners fail the 0.4 V headroom allowance. They are not concealed
as passing operating conditions. Measure the actual X cable DC loop resistance
before installation. Regulator thermal rise depends on board assembly and air
flow; the electrical dissipation calculation is not a thermal qualification.

The 1/1.5/2 m comparisons all use the same 2 m mast and 25° downward slope.
Sky temperatures are NEC beam-weighted PyGDSM16 estimates over sidereal time at
54.12° N, with a 50 Ω noise approximation. At 50 MHz, 1.5 m arms give roughly
2.9 dBi realized zenith gain and 4.8 kK median system temperature in this model.
The separate 2.15 m case remains the 32.55 MHz SIMONe candidate.

## Files and reproduction

- `end_to_end.py`: cascade and DC sweep; results in `end_to_end.h5` and JSON summary.
- `validate.py`: independent ngspice passband/tolerance calculations.
- `antenna/`: NEC2 and PyGDSM calculations, convergence checks and HDF5 data.
- `plot_end_to_end.py`: emits the Rustplotlib plotting program.

Run Python programs with `conda run -n base python ...`. Recompute antenna and sky
products first if geometry, location, circuit loss or receiver assumptions change.
Active-device IP3/P1dB remain datasheet-based budgets; no nonlinear simulation
or blocking/recovery qualification is claimed. PCB cross-coupling, common-mode
coax currents and oscillation/stability require further modelling or measurement.

The added common-mode choke and bead contribute at most 0.17 ohm at 20 C
to the DC loop, included in the corner calculation. The RF cascade still
uses the bypassed-supply approximation; it does not predict conducted-RFI
suppression or noise improvement from this new filter.
