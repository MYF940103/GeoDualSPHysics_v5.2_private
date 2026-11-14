# C08 pressure-feedback r2: defined wall-observer scope

Author-only; no build/component/solver/native/VTK/Git/SHA action performed. Root separately reads and admits the new private build and one bounded component. r1 numerical results are not reclassified as passed.

## Actual r1 status and narrow correction

The original r1 component returned1 in both actual exit captures, with no ownership failure or surviving process. Its first Part38 baseline passed the5000 actual Ace/six stress-rate/theta/pressure-rate/FS bit comparisons and wrote one baseline trials row. The first constant+1Pa trial stopped at the compound active-wall derivative/C diagnostic assertion. It did not perform a time update. That error did not print a first offending native ID, so none is inferred or invented. The original r1 failed receipt/output and separate link_r2 program remain unchanged.

The observer erroneously defined active as mode!=BMODE_MDBC2OFF, thereby treating ignored modeDBC0 as reconstructed active mDBC. The original schema2 source establishes the actual range:

- JSphCpuSingle.cpp609: NpbOk=Npb−GetNpbIgnore(), retaining ignored fixed IDs in the total Npb allocation.
- JCellDivCpuSingle.cpp327–330: cell presort computes the BoxBoundIgnore count, separate from out/excluded particles.
- JSphCpuSingle.cpp762: normal mDBC correction resets all BoundModec to BMODE_DBC0.
- JSphCpu_mdbc.cpp1125–1145: DynamicWall classifies only indices[0,NpbOk) into BMODE_MDBC2 or BMODE_MDBC2OFF from actual support.
- JSphCpu_mdbc.cpp1190/1198–1203 and1219/1227–1231: ghost state/C interpolation is limited to NpbOk, skips OFF receivers, and validates only processed active values. Ignored and OFF derivative/C scratch is not a defined field to compare.

These positions refer to the exact original src/source files inside outputs/c08_preload_schema2_source_r1/full_source.zip, already bound by the original86-object build. No public source is edited. The retained p38 wall count was mode0=857, mode1=571, mode2=377; r2 reports actual counts in every trial rather than hardcoding571 into a general gate.

New r2 requires i<NpbOk implies modeMDBC2 or modeMDBC2OFF, and i>=NpbOk implies modeDBC0. It reads derivative/tangent/C scratch only for i<NpbOk AND modeMDBC2. All1805 fixed-particle nonpressure primary checks (position, physical velocity, sigma-effective, J, P0 and mode/ID) remain; all truly active scratch bits remain required. Every call records NpbOk, active, inactive-effective and ignored counts. Their sum must be1805; NpbOk=active+inactive; ignored=Npb−NpbOk. Compared with its own same-state baseline, NpbOk, all counts and each ID's active/ignored/mode identity must be unchanged. This is a correction to the new diagnostic's undefined-read scope, not a physical bug fix, relaxed valid-wall equality, changed wall reconstruction, or changed numerical tolerance. Old invalid ignored scratch is not read again or reconstructed from prior garbage.

## Everything else unchanged

The new entry is mechanically derived from the frozen r1 CPP by an exact finite replacement table: new tag/output/build paths, diagnostic wall scope/count/identity fields and reporting only. The builder verifies every replacement count and byte-equality of the resulting source. All original state Restore/Map/Roles/Ledger/Unchanged routines and original RHS literal/decomposition source fragments remain byte-identical. The setup and no-fixed-neighbor receiver mask remain original. The only AppInfo change is the diagnostic program label.

The experiment remains Parts38/76,17 original force/Darcy calls each (baseline plus four pressure modes×two magnitudes×both signs),34 total, zero physical/material updates. Original5000 baseline float bits, pressure-only soil primary equality, theta/six stress-rate/C/FS/normal equality, original literal-float/donor and seven-double-channel reconciliation budgets remain unchanged. The eighth numerical rate residual stays separate. Actual float pressure perturbations, signed central Q with w=nV/Kw, amplitude/quantization reporting and the lack of any physical sign gate remain as documented by r1. No new physical parameter, trial, half chain, PRE, cap/PONDING or changed AS is admitted.

Outputs retain80000 central response rows,64 focus rows,48 cohort summaries and34 trials, but use exclusive outputs/c08_h18_pressure_feedback_r2. trials.csv adds four real wall-partition counts. baseline_p and fixed_P0 remain distinct. Completion explicitly marks the legal scratch scope and partition identity checks. No full coupled spectrum, new trajectory or physical acceptance is asserted.

## Build contract

The new builder uses one new r2 entry object plus the same86 original DebugCPU physical objects,160 protected archived headers and7 runtime companions. It does not rebuild the physics or use public headers. Its actual dependency audit correctly requires JSph.h/JSphCpu.h/JSphCpuSingle.h/FunSphKernel.h and all four generated includes. The unused FunSoilMaterial.h is no longer required to be directly included; its original archived stat remains protected. The original r1 CPP, failed build/component receipts and successful link_r2 receipt are preserved as consumed evidence. Source/profile arithmetic gates are not changed.

Root-only later build command: python -B tests/support/c08_h18_pressure_feedback_r2_build.py --execution-authorized. This compiles/links only, never runs the component. After an independent passed build, root may uniquely invoke the exact same original full301 native and full3 seed with original CPU1 flags into the fresh r2 output. No old failed output may be overwritten; no component or next solver follows automatically.
