# Private CPU TPI-X0 short-window assets (authoring only)

This is one fresh case02 1040-ID/22-array implementation and phase diagnostic. It does not modify formal inputs or claim a physical release. The parent C08 task decides each build/run/native admission separately. Preparing these assets launches no program.

## Common input

`support/upl_tpi_x0_short_r1_prepare.py --execution-authorized` exclusively creates `configs/upl_tpi_x0_short_r1_Def.xml`, `configs/upl_tpi_x0_short_r1.clock.csv` and `logs/upl_tpi_x0_short_r1.prepare.json` after root review. Existing files are protected, including partial preparation. The base is `configs/upl_column_public_coarse_r1.xml`; its complete case definition, generated geometry/constants, material, X periodicity, FreeSlip bottom, band load and .01 s drainage/ramp events remain. The explicit changes are 5 us initial/fixed step, .15 s endpoint, .001 s output, AV=.1, G1, SPR1, damping=.04, HG0. Only the special multi-segment timeout is removed. Shepard remains OFF.

The closed source configuration accepts SPR1 for this loaded column. `JSphCpu_mdbc.cpp::ComputeBoundaryDerivativeVelocity` returns when DynamicPoreWall is active because the dynamic wall supplies the authoritative same-stage J-weighted mirror; SPR1 therefore does not imply an additional reconstruction. Its initialization still checks the real bottom plane normals; this must pass the actual program, not be bypassed.

The proposed three independent CPU programs are the frozen original, private default-OFF, then private X0-ON. OFF must reproduce the original same-CPU native fields and signed clock diagnostics exactly before ON is admitted. No retained exact 5 us/HG0/AV.1/damping.04/.15 s control was found. This is one bounded control, not a half-step chain. The ON variant removes finite water storage in its row; cross-model differences are descriptive, never a 5-Pa half-step/physical-accuracy gate.

## Actual clock and native reader

The plan replays binary64 scalar `time += 5e-6`, the original one-segment `JDsOutputTime::GetNextTime`, the TimeMax crossing and zero-based native Step. It never replaces actual clocks with n*dt, snaps an event, interpolates a frame or rewrites saved metadata. With normal .001 s saves, the completed-2000 pre-open event may have no native save because its scalar clock is slightly below .01 s. The plan records that absence explicitly. The first actual later saved frame is post-open; the X0 sidecar/source-stage checks, rather than a fabricated native event frame, must verify the unchanged event policy.

`support/upl_tpi_x0_short_r1_native.cpp` derives the original column typed decoder and its native rest/lattice, 1040 IDs, 22 array types/counts, fixed markers, J/n/V/rho/k ledger, double-stress display, all-direction FS2/3 drainage and signed necessary-step checks. Its closed plan parser independently reproduces the .15 s scheduling and compares every CSV row. It adds `typed22.bin` in an explicit fixed-ID array layout (the original 15 typed arrays followed by six original dynamic doubles and original float PosDiv) for a genuine OFF/reference typed payload comparison. Header schemas and source counts remain original; no claimed BI4 file identity follows from this canonical export.

The reader does not observe force-stage loading, private TPI history, actual owned solver exits, source/executable identity, post-.1 s stress/top-gap safety or physical theory accuracy. Root must check those independently. Its J ledger remains the original finite saturated grain-volume identity, not an assertion that beta-zero pressure retained finite Kw physics. It rejects data/plan/output reuse or overwrite; failed analyses remain preserved.

No reader has been built or run at authoring. No solver, GenCase, VTK or physical acceptance is implied. No full consolidation, restart, CPU/GPU, C08 collapse or other-psi run is admitted by these files.

## Separately admitted reader build

`support/upl_tpi_x0_short_r1_reader_build.py --execution-authorized` is one compile/link action only. It consumes the successful private `c08_h18_as03_rhs_r1` DebugCPU compiler/link recipe, its 86 retained non-main authoritative objects, 160 frozen headers and seven runtime leaves. Only the entry source/output names change. The exact same local original22 core is an actual compiler dependency. The script reuses the existing Win32/Popen call owner helper with this case02 log directory; it never edits that helper, the frozen headers/objects, public source or canonical programs. It records stat bindings and actual compiler/link exits, performs no SHA scans, protects any previous/partial build and never invokes the resulting reader. The intended output is `outputs/upl_tpi_x0_short_r1_reader_build/UplTpiX0ShortNative.exe`; the build receipt is `logs/upl_tpi_x0_short_r1_reader.build.json`.
