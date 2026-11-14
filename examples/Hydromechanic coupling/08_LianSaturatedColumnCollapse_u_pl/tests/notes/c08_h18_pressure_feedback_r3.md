# C08 pressure-feedback r3: ignored mode is not defined metadata

Author-only; root must separately review/admit the new build and one component. No author execution/import/build/component/solver/native/VTK/Git/SHA was performed. All original r1/r2 failures, sources, generated fragments and programs remain unchanged.

## What failed, and the actual source correction

r1's Part38 baseline passed all5000 actual RHS bit comparisons, then its first constant+1Pa attempt stopped at a compound wall-scratch equality assertion. r1 incorrectly treated every mode other than OFF as an active reconstructed wall, including ignored mode0 storage. The subsequent r2 was a diagnostic-only attempt to bound active scratch correctly, but added a second unsupported assumption that every ignored tail mode must be0. Its actual component returned1 before any completed trials row, at the sorted effective/ignored wall-mode assertion. Neither error printed an offending ID; none is invented. There was no time advance or new physical trajectory, and r2 produced no complete baseline qualification.

The prior r2 author note's reference to a per-force mode reset was wrong for this path. Exact schema2 archive outputs/c08_preload_schema2_source_r1/full_source.zip establishes:

- JSphCpu.cpp652/665: InitRunCpu initially sets BoundModec to BMODE_DBC0. InitRunCpu is initialization, not PreInteraction_Forces.
- JSphCpuSingle.cpp685–693: DynamicPoreWall enters the dedicated empty branch and bypasses MdbcBoundCorrection. Therefore its line762 reset is NOT performed during the current dynamic-wall force path.
- JSphCpuSingle.cpp609: NpbOk=Npb−GetNpbIgnore(); ignored fixed IDs remain in the complete Npb allocation.
- JCellDivCpuSingle.cpp113–114 and327–330: normal boundary cells precede BoxBoundIgnore, followed by fluid cells; sorting produces the effective prefix and ignored fixed tail.
- JSphCpu_mdbc.cpp1125–1145: current DynamicWall only overwrites modes in[0,NpbOk) with MDBC2 or MDBC2OFF. State/matrix interpolation at1190/1219 is likewise limited to NpbOk and skips OFF. Ignored values can retain earlier classification and are not a current physical mode field.

Thus neither a stored0 count nor a past table proves the ignored ID set. The new observer must not read ignored BoundModec at all. This is a correction to the new diagnostic's observation contract; no claim of a physical solver bug or repair is made. Old UB scratch is not replayed or reinterpreted.

## Exact r3 scope

From the frozen r2 CPP, only eight mechanical substitutions are allowed: new tag/path, ignored-mode read/classification, conditional valid-mode equality, explicit completion metadata, a diagnostic formatting helper, field-labelled mode/primary errors and split active derivative/tangent/C errors. The build recipe verifies exact occurrence counts[7,1,1,1,1,1,1,1] and byte-equality of the resulting r3 source. All pressure perturbation arithmetic, original actual force calls, original RHS/source-order and float/donor budgets,5000 baseline bit checks, soil invariants and Q calculations are unchanged.

For every fixed ID, ignored means exactly i>=NpbOk. Its local diagnostic Wall.mode is set to255; no original array is written, and ignored BoundModec/derivative/tangent/C are not read. For i<NpbOk only, mode is read and must be MDBC2 or MDBC2OFF; trueactive is that valid-prefix membership AND modeMDBC2. Only trueactive derivative/tangent/C are compared bitwise. Mode equality is checked only for the effective prefix; ignored sentinel equality is not presented as a physical mode comparison. Mode and primary failures print the real native ID, current index and NpbOk. Active derivative/tangent/C are the same individual bit-equality requirements, checked separately with their actual field name and the same ID/index/NpbOk context; only diagnostic reporting is split.

All1805 fixed particles still require exact ID, ignored membership, position, physical velocity, sigma-effective, J and P0 equality against the same-state baseline. Effective wall mode and active status remain exact. NpbOk and actual active/inactive-effective/ignored counts are frozen; active+inactive=NpbOk, ignored=Npb−NpbOk and all sum to1805. The sentinel is diagnostic-only. A change in real effective mode or actual ignored membership is still a failed conditional-state experiment.

The component remains Parts38/76,17 calls each and34 total, zero physical/material steps, the same four pressure modes at±1/±10Pa, and the same original PRE/source/runtime/AS/AV/NoPen/FS policies. No cap/PONDING/filter, new parameter, control, half chain, decoder or solver is added. The seven physical RHS channels plus a separate eighth signed numeric residual remain unchanged. Q uses actual quantized central pressure and w=nV/Kw; no Q sign or constant-mode null is a physical pass gate.

Outputs are exclusive outputs/c08_h18_pressure_feedback_r3:34 trials with real wall-partition counts,80000 response rows,64 focus rows,48 summary rows and completion. Failed prior outputs are not overwritten. Baseline pressure and fixed P0 remain distinct. This conditional subsystem is not a full coupled stability spectrum or physical acceptance.

## Private build only

The new r3 builder retains one fresh entry object plus86 original physical objects,160 protected archived headers and7 runtime companions. It preserves all earlier RHS/global_modes/native/PRE/stat bindings and adds the original r1/r2 failure/build/call records as evidence. The actual four required headers and four original numerical includes are required; unused FunSoilMaterial.h is not a direct-include requirement but stays stat-protected in the archive. No physical source/ABI/object or canonical executable changes. Only diagnostic AppInfo changes to the r3 label.

Root-only later build: python -B tests/support/c08_h18_pressure_feedback_r3_build.py --execution-authorized. This never runs the component. A separately admitted unique invocation would use the same original full301 native, seed and CPU1 flags into the new r3 output. Exit0 or a correct observation contract is not an accepted physical solution, and no next computation follows automatically.
