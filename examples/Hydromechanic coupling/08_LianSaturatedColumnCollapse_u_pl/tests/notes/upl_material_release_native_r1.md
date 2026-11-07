# Unified material short implementation regression (author-only)

This new tag is prepared but has not been built, decoded or physically run by the author. Old source, formal inputs, runtime_r2, old programs and all retained outputs remain unchanged. No watcher or automatic next job is created.

## Files and programs

- Owner: `support/upl_material_release_native_r1_run.py PROFILE CPU|GPU --execution-authorized`; one requested job only.
- Current-ABI reader builder: `support/upl_material_release_native_r1_build.py`; consume only `logs/upl_material_release_DebugCPU_r3.build.json`, its 86 project objects minus main (85). It does not use old objects.
- Independent decoder: `support/upl_material_release_native_r1_decode.py PROFILE CPU|GPU --execution-authorized`; one completed owned run only, never reruns the solver.
- Offline reviewer: `support/upl_material_release_native_r1_review.py baseline|alias|receive_old|receive_new CPU|GPU`, or `cross source|plastic`. It never decodes or runs programs.
- Profiles: source, alias0, receive_old, receive_new, fluid, plastic. Twelve new XML files are under `configs/upl_material_release_native_r1_PROFILE_BACKEND.xml`. Generated seed copies, solver data and exports are shallow under `outputs/upl_material_release_native_r1_PROFILE_BACKEND*`; logs and checks are under logs; comparison CSVs are under figures.
- CPU program receipt: `logs/upl_material_release_DebugCPU_r3.build.json`; actual program `outputs/upl_material_release_DebugCPU_r3/DualSPHysics5.2CPU_win64_debug.exe`.
- GPU receipt: `logs/upl_material_release_Debug_r3.build.json`; actual program `outputs/upl_material_release_Debug_r3/DualSPHysics5.2_win64_debug.exe`. The owner requires the matching passed actual build and captured program/archive, and separately stat-checks copied Chrono/config/OpenMP runtime against the frozen prior runtime copies.

## Explicit gated order for the root reviewer

For each backend, run and decode source, then review baseline against retained old-r2 source (22 frames/all22 payloads and complete original signed clock CSV). Run/decode alias0 and review against its new alias1 source. Source and alias0 are the identical 800-update, 2.5-microsecond Ck2 profile including the real completed380 PRE and one declared 260-wall retirement; only alias value differs. No GenCase is needed or invoked.

For receive_old, consume the already certified historical same-backend `upl_preload_handoff_source_BACKEND_r1/data/Part_0010.bi4` (typed old MR1, no new version key). For receive_new, require the new source native check and its typed MaterialLawVersion2 PRE, whose configured expected path is its `Part_0010.bi4`; the owner verifies that actual certified file before launch. Each receiver performs420 new updates to global800, with nonzero actual Part0 time. Compare all11 post-release common states, every22 typed payload and actual saved clocks/signed intervals, by native ID. It is an observed post-advance continuity check, not an independently observed pre-advance exact import snapshot.

Purefluid uses the retained1024-particle periodic seed without regeneration. It disables HydroMech/dynamic and has E/strength/dilation/residual/decay all zero; decimal dt1 microsecond, four updates, output1 microsecond. Its independent reader checks seven existing typed arrays, all IDs, finite values, zero kappa, actual clock, signed safety and absence of soil-version metadata. It deliberately does not require the22-array coupled schema.

Plastic uses the same retained1024-particle, 32x32 XZ-periodic velocity seed. New decimal dt1 microsecond,256 updates and output64 microseconds. It must actually produce nonzero kappa, preserve all22 arrays/IDs/J-volume/rho/k ledger, float cache bits, monotonic completed-state history and original signed safety. It is not expected byte-identical to the older128-update dyadic trajectory. CPU must have a passed native gate before GPU is launched; independently review actual matched CPU/GPU saved steps with pressure RMS<=5Pa and material displacement maximum<=.005mm. Source CPU/GPU uses the same bounds separately. All field differences, including total stress, J/n/k/kappa/FS, are reported; they are not silently required bit-identical across backends.

The native reader only accepts new trajectory metadata typed uint MaterialLawVersion=2 and typed sf=0; the dedicated PRE helper keeps schema1 and original contract, accepts old typedMR1 only when the new key is absent, and never falls back from an unknown or wrongly typed new key. Old reader/build/run receipts are not changed.

## Limits and deferred checks

These are implementation regressions, not a new full collapse,10-second preload-equilibrium, general restart, physical or performance acceptance. No half-step or new long solver chain is introduced. Native completed-state monotonicity and the5-frame plastic trajectory do not prove predictor history preservation or periodic ghost-copy correctness. Direct actual step-level Pre/Cor and periodic-copy component probes remain separate root tasks. Verlet spatial validation is deliberately not launched; the dynamic public admission remains Symplectic-only. Corrupt metadata fixtures and generic PART rejection tests are separate host-loader tests, not aliases of successful handoff.

Consumed programs, inputs, old PRE/raw states, current source archive and runtime copies use necessary stat/receipt bindings; this stage performs no SHA scans. Existing partial or terminal artifacts reject same-tag reruns. Any failed analysis is inspected offline and never used as a reason to rerun a completed solver.
