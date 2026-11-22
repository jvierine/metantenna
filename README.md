# Metantenna — 30–70 MHz X/Y receive antenna

Engineering prototype for meteor-radar reception, centered on SIMONe's
32.55 MHz operation. Two independent 50-ohm SMA outputs carry X and Y signals
and receive 12 V DC through a dual indoor bias tee. Circular polarization can
be formed digitally from calibrated coherent receiver channels.

**Development status:** passive-filter SPICE and geometric routing checks pass.
Native KiCad checking, component availability/pricing, and complete mechanical
review are in progress. This is not a field-qualified design or a production
release. Do not infer amplifier, antenna, or weather qualification from the
passive-filter simulations.

The electronics budget includes both preamps and the dual bias tee; it excludes
coax, mast, enclosure, tax, and shipping. The goal is below USD 100 per complete
electronics set. No order has been placed.

The requested prototype batch is **five antenna/preamp boards and five dual
bias-tee boards**, giving five complete electronics sets, delivered to
**Norway**. The electronics budget is therefore below USD 500 for the batch,
excluding coax, mast, enclosure, tax, and shipping. Supplier quotations must
separate those excluded costs and distinguish bare PCBs from populated boards.

- `hardware/`: electrical source, editable KiCad boards/schematics, reproducible routing.
- `simulation/`: ngspice deck, independent network calculation, 300 tolerance trials,
  HDF5 results and quantified limits.
- `mechanical/`: parametric Python/Manifold CAD and checked printable STL parts.
- `manufacturing/`: prototype Gerbers, drills and assembly workbooks.
- `docs/`: drawings and assembly/test instructions.

The architecture is inspired by a crossed-dipole active antenna head, but is
**not a copy of LOFAR's high-input-impedance differential LNA**. This revision
uses an isolated 1:1 feed transformer and matched MMIC channels; antenna
impedance and element dimensions must be validated separately. Broadband
electronics alone do not establish broadband antenna efficiency or pattern.

## Reproduce the work

Use base conda Python with numpy, scipy, h5py, shapely, manifold3d, trimesh,
Pillow and openpyxl, plus ngspice. Plotting uses the sibling checkout
`../rustplotlib` and Rust; no Matplotlib is used by the project.

```sh
conda run -n base python simulation/validate.py
conda run -n base python hardware/build.py
conda run -n base python hardware/schematic.py
conda run -n base python hardware/check_layout.py
conda run -n base python hardware/export_fab.py
conda run -n base python mechanical/build_enclosure.py
conda run -n base python simulation/prepare_plot.py
cargo run --release --manifest-path tools/plot/Cargo.toml
```

The synthesis optimizer is `simulation/design_filter.py`; ordinary rebuilds
use the already-selected component values. Simulation results are HDF5,
assembly tables are XLSX, and no scientific CSV products are written.
