# SURTR VHF antenna head

Both factory-assembled SMA jacks sit over the 50 mm mast socket. The enclosure mounts the PCB component-side down, so the two coax cables pass straight into the pipe. Feed the plugs through with the board lifted, connect X and Y, then lower and fasten the board. The symmetric rain hood fits the shallow base.

![Straight coax paths through the mast socket](mechanical/center_sma_cable_entry.png)

The case is modeled for a pipe with at least a 36 mm inner diameter and plugs up to 12 mm in diameter. The 35 mm socket is the only feature below the housing floor.

KiCad ERC, DRC, and schematic parity passed. The X output runs on the back copper over the inner ground plane, with ground stitching at its transition. The Y output stays on the component side. Both use 0.34 mm nominal traces for a 50 Ω target with approximately 0.21 mm outer dielectric. Confirm the stackup and impedance with the fabricator. Isolation and amplifier stability still need bench verification. This candidate has not been uploaded to JLCPCB or physically fit-tested.

| Board | Routing and labels | Silkscreen | Copper layers | 3D placement |
| --- | --- | --- | --- | --- |
| Antenna head | [Routing](mechanical/preamp_routing.png) | [Front](mechanical/preamp_front_silkscreen.png) | [L1–L4](mechanical/preamp_copper_layers.png) | [Package view](mechanical/preamp_3d_placement.png) |
| Bias tee | [Routing](mechanical/biastee_routing.png) | [Front](mechanical/biastee_front_silkscreen.png) | [L1–L4](mechanical/biastee_copper_layers.png) | [Package view](mechanical/biastee_3d_placement.png) |

[RF layout review](docs/RF_LAYOUT.md)

[Manufacturing package](manufacturing/vhf_jlc_sourcing_QUOTATION.zip) · [End-to-end model results](simulation/end_to_end_results.json)

[KiCad board](hardware/preamp.kicad_pcb) · [Printable base](mechanical/stl/base.stl) · [Symmetric hood](mechanical/stl/rain_hood.stl)
