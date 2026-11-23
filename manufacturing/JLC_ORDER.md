# Rev B prototype order — five sets

Order **5 preamp PCBs and 5 indoor bias-tee PCBs**, as two separate board orders.
Use the contents of `jlc_rev_b/`, not the older custom-export prototype archives.
The combined downloadable package is `metantenna_rev_b_jlc_package.zip`.

For each board:

1. Upload its `Gerbers.zip`. Select **4 layers, 1.6 mm FR-4, standard stackup,
   1 oz outer copper, 0.5 oz inner copper, green mask, lead-free ENIG**.
   No impedance-control surcharge, via filling or via-in-pad process is specified.
   L1 is top RF/local connections; L2 and L3 are GND; L4 carries antenna/DC connections.
2. Choose **top-side SMT assembly** and upload `BOM.xlsx` and `CPL.xlsx`.
   Excel is intentional. Coordinates are millimetres in the native Gerber frame:
   X right, Y up; the board extends into negative Y. Do not independently shift
   or mirror either file. DNP parts and hand-installed connectors are excluded.
3. Match the **exact manufacturer part numbers**. The LCSC column is blank
   until JLC confirms its matches. Do not approve automatic substitutes for
   transformers, MMICs, LDOs or RF inductors. Coilcraft Q/SRF and C0G capacitors
   matter. If a part is unavailable, use JLC sourcing/consignment or stop for a
   component review; a footprint-compatible substitute is not automatically RF-equivalent.
4. Inspect every polarized/numbered part in the placement preview, including
   ADT1-1+ pin 1, GALI-74+ IN/OUT, TPS7A4901 pin 1 and diode cathodes.
   JLC's rotation convention can differ from KiCad's. Approve only the actual preview.
5. Check the four copper layers, solder-mask openings, plated/NPTH drills,
   and dimensions: **96 × 96 mm preamp; 76 × 64 mm indoor board**.

`Hand_assembly.xlsx` lists the SMA and power connectors to procure and solder
separately. For a quote with factory-installed connectors, use the paired
`BOM_full_assembly.xlsx` and `CPL_full_assembly.xlsx` instead; that option needs
JLC confirmation of through-hole assembly and the underside SMA operation.
Do not mix a full-assembly BOM with an SMT-only CPL. The preamp SMA bodies go on the **underside**, pointing down; the
indoor connectors are **Amphenol 132203 right-angle bulkhead jacks on top**.
J10/J20 point left toward the antenna cables; J11/J21 point right toward
the receiver cables. They exit the printed case sidewalls, not its lid.
Use the new biastee_base.stl and biastee_lid.stl; 2 mm panels accommodate
the connector maximum 2.4 mm panel thickness. The open-top U-slots accept the assembled board: remove connector nuts and
washers, lower the PCB vertically, secure it, fit the lid and then the nuts.
The lid tongues close the slots. Fit the board loosely, align
the four side jacks, and use thin spacer washers if needed between the jack
shoulder and case. Do not bend the PCB by tightening a nut across a gap. Standard female SMA, not RP-SMA. Antenna copper
arms solder directly to X±/Y±; they need no RF connectors.

The purchase is a **prototype order**, not certification of RF performance.
Native ERC/DRC reports and exact-source manifest accompany each board. Part
matching, assembly preview and manufacturer CAM acceptance must be completed
before payment. No order has been placed and no delivered price is quoted.

## Installation and first power-up

Use a current-limited regulated **12 V supply (minimum 11.76 V)**. Only X carries
DC. For up to 50 m coax, the X cable's measured center-plus-shield DC loop
resistance must be **≤3 Ω**. Modelled RF loss is 5 dB at 50 MHz; use the actual
cable specification for the receiver budget. Y is RF-only.

First check resistance, apply power with a current limit, verify ~8.07 V at each
LDO and roughly 75–85 mA amplifier current at room temperature. Do not connect
the receiver until both receiver-side bias-tee outputs have been checked for DC.
Then measure VNA response and stability, two-tone linearity and strong-signal
recovery before unattended field use. No transmit-site overload rating is claimed.
