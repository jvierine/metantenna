# Open antenna designs

**TL;DR:** Open-source antenna hardware designs aimed at high performance. We hope anyone can take a design, make the changes they need, and have the boards assembled by a turn-key manufacturer.

| Design | Intended use | Status |
| --- | --- | --- |
| [VHF meteor-radar antenna](vhf/) | Crossed dipoles, independent X/Y outputs; 30–55 MHz electronics, arm lengths selected for the radar frequency | Engineering prototype; modeled sensitivity and fabrication files available |
| [HF active antenna](hf/) | Balanced high-impedance input; nominal 0.1–30 MHz | Development prototype; sensitivity and linearity not yet qualified |

Both designs use 50 Ω coax outputs, a 12 V bias tee and common-mode filtering. The HF input architecture differs from the approximately 50 Ω VHF input.

[VHF single-sided manufacturing variant](variants/vhf-jlc/)

## SURTR · VHF meteor radar

![SURTR, an inverted-V antenna under a meteor streak](docs/surtr-banner.png)

**Specular-scatter Unit for Receiving Trail Returns**

[SURTR antenna head with centered SMA connectors](variants/vhf-jlc-center/)

![VHF antenna deployment](vhf/docs/antenna_deployment.png)
![VHF antenna PCB with critical components](vhf/docs/preamp_rev_b_annotated.png)

**VHF indoor bias tee — power injection and filtering at the receiver.**

![VHF bias-tee PCB](vhf/docs/biastee_layout.png)

## HF example

![HF active antenna PCB](hf/docs/hf_preamp_layout.png)

**HF indoor bias tee — separate low-frequency common-mode filtering.**

![HF bias-tee PCB](hf/docs/hf_biastee_layout.png)

The design folders contain the schematics, PCB layouts, simulation results and manufacturing guidance. Shared [mechanical designs](mechanical/), [modeling code](simulation/) and [CAD generators](hardware/) are kept at the repository root.

[NEC impedance models](models/nec/) cover 1 m, 1.5 m and 2 m arms from 0.1 to 150 MHz in 0.05 MHz steps, with complex X/Y feedpoint impedance in HDF5.

These are open engineering prototypes, not certified products. Simulation and CAD checks do not replace RF measurements of assembled boards. No manufacturing order has been placed. The five-set VHF electronics budget is $70–100 per set including the bias tee, excluding coax, mast, enclosure, tax and shipping; this is an estimate, not a supplier quote.

## KiCad version for collaboration

Use **KiCad 10.0.x stable** for these designs. Nico uses 10.0.5; local validation used 10.0.8. KiCad documents point releases as file-compatible. Avoid saving shared files with a newer major version or a nightly build until the team agrees to migrate. Project-local symbols and footprints are included; retain `sym-lib-table`, `fp-lib-table` and the adjacent library directories when copying a design.

`main` is the integrated working version: VHF and HF designs, retained common-mode filtering, and Nico's reviewed VHF hierarchy/coupling updates. `pfeffer-review` remains Nico's review branch.
