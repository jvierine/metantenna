# Crossed-dipole NEC impedance models

`crossed_dipole_impedance_0p1_150MHz.h5` contains complex impedances for **1 m, 1.5 m and 2 m per-arm lengths**. The common frequency axis is 0.1–150 MHz inclusive in 0.05 MHz steps (2,999 samples).

Each geometry group (`arms_1m`, `arms_1.5m`, `arms_2m`) contains:

- `feedpoint_impedance_ohm`: complex impedance, dimensions `[frequency, polarization]`; polarization is X then Y.
- `arm_half_circuit_impedance_ohm`: dimensions `[frequency, polarization, arm]`, equal to half the balanced feedpoint impedance. This is a **symmetric differential half-circuit referenced to a virtual midpoint**, not an independently calculated arm-to-earth impedance.
- `convergence_61_segments`: denser-mesh results at nine check frequencies and the relative complex-impedance discrepancy.
- Geometry, soil and termination attributes.

The reference model uses 2 mm diameter copper wire, 25° downward arm slope, X/Y feed heights 2.00/2.01 m, 86 mm feed bridges, nonconducting mast, and homogeneous ground with relative permittivity 13 and conductivity 0.005 S/m. The unexcited orthogonal port is terminated in 50 Ω. PCB, enclosure, cable/common-mode currents and local ground structures are omitted. Recalculate the model when changing these assumptions.

The six `.nec` files are the actual solver input decks. The sweep uses 41 segments per arm; `convergence.json` records comparison with 61. Sampled convergence is a numerical check, not experimental validation or a full electromagnetic model of the installed antenna. The frequency grid does not imply the electronics or sky model are valid across the whole grid.

Reproduce from the repository root with base conda Python and a compiled `nec2c` solver:

```bash
NEC2C=/path/to/nec2c conda run -n base python simulation/antenna/wideband.py
```

The file metadata records the solver revision and binary hash. All impedances are in ohms, using the complex convention `R + jX`.
