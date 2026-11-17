# P3 bounded2s scientific adapter r1

Author-only draft; no scientific analysis, native read, solver, build, VTK, queue, Git or SHA action executed. The unique P3 long-window run and its frozen dependencies are not changed. New files are `tests/support/upl_tpi_p3_window_review_r1.py` and this note.

The actual new candidate is `upl_tpi_p3_B10us_window2s_GPU_r1`. Writing this script does not admit a reader, analysis or next solver. It only accepts a completed genuine P3 run plus independently passed unique native read/review. A solver exit alone cannot satisfy it.

## Thin reuse without hidden old large-table reads

Imports do not call an old main or modify any module globals. The adapter directly reuses causal.Admission pin/read/table/finish, binary/stat/write tools, causal.references/describe/events, staged.old_arrays and the existing scalar-difference arithmetic. The literal original target inequalities and actual nearest-saved selections are retained in a small local target wrapper, rather than disguising real P2 as B10 to satisfy a hardcoded role name.

The original staged.differences tail requires1000-ID old n/rho arrays and would force another P2 ledger pass or fabricated native arrays. This candidate instead copies only its real ID/pressure/minimum-image XYZ/scalar arithmetic. Its new layer table adds only real P2 physical-derived pressure, settlement, J, alternating Uz and six total stresses. P2 per-layer n/rho is not manufactured; P2 scalar n/rho context comes from already verified history. This scoped copy was explicitly selected to avoid the old ledger dependency.

New P3 uses physical.bin, soil_n.bin, clock.bin, IDs, completion, native history and exactly one streamed native ledger pass. Ledger ID/time/J/n/density association is checked before the original100-layer describe function uses the actual density. New momentum/total-stress diagnostics retain the original physical meaning; saved LoadAce is not promoted to a same-stage applied-force or coupled-energy certificate.

A/B10/P2 context uses the completed P2 scientific check/metrics/history/profiles/targets/events. No A or B10 binary, ledger or old scientific main is reloaded. The only old large binary is the already decoded P2 physical.bin for all-ID pressure/XYZ and full Uz/stress mode maps, plus clock.bin/IDs/schema/completion. P2 soil_n and ledger are not read. Earlier staged-P1 conclusions are inherited from preserved P2 metrics only, with no staged dataset or44-column loadclock requirement.

## Exact source and native profile

New run tag/stage, actual read/review stages, job tag/run stat/output/native path/plan bindings must all be genuine P3. The unique read invocation is1 and the passed native review must retain all22 guards, all1040 original IDs and the fixed40/soil1000 common26 schema.

Profile remains Release/B/window2s,199996 updates/1263 saves, dt=`1.0000228881835938e-5 s`, actual scalar end=`2.00000577545594 s`. Source event completed1000 is pre-open and1001 post-open;1159 post-open saves remain covered. Required review evidence includes all1263 five-phase intervals/1262 actual signed checks, all1263000 saved ID triplets, all3*1263000 pressure observations, q2=actualp1/q3=actualp2, zero added tolerance and original physical HG forcecalls2N/predictorN/correctorN.

The actual final native rate is R3 evaluated at actual p2, not R(p3) or dp/dt. It is not used to invent an endpoint convergence or second-order claim. The generic native body proves original native safety only; its stage is not substituted for new P3 pressure semantics.

P2 source remains its own original `upl_tpi_p2_B10us_window2s_GPU_r1` run/read/review, correctly bound and passed. The P2 completion/schema/IDs and physical/clock files are stat-admitted. Its actual immutable plan must equal P3's original plan. Every P2/P3 actual time/Step/dt bit and original material coordinate must match. Signed intervals are guarded independently, not required numerically equal. Initial signed values are retained and noninitial empty sentinels rejected. No nearest native pairing, interpolation or clock rewriting is used.

## Budgets, references and retained failure

Original constants and512-mode companions remain unfitted. New P3 uses M0 at its own actual times; A keeps its own finite-Kw companion and sampling. No time/load/radius/k/parameter fit or extra tolerance is added. Finite-ramp, kernel-band load, inertia/current-J startup and boundary limitations remain those of the original diagnostic companion.

The two original covered targets remain legacy Tv=.005 and .05, selected at actual nearest saved states with target gaps explicit. Literal tests are unchanged:

- Pressure layer-mean profile RMS <= original A actual-time error +10Pa.
- Absolute top-material settlement error <= original A +.001*S_infinity (approximately .003714285714mm).
- Absolute bottom-material error <=.005mm and <= original A +.002mm.

Original A target part/time/errors and the four retained limit values must match the already completed P2 target table. Old B10/P2 errors and failed budgets remain explicit descriptive context; an old A failure never exempts P3. The original P2 first-target top failure is not reclassified by this script.

Every new saved state at t>=.1-1e-7s is checked by the unchanged describe function: maximum of all100 mean-layer total sigma_zz errors and the top-two-layer gap must each be<=100Pa. Full startup and1.5-2s late fields remain visible, without smoothing/filtering or a late-only exemption. Later full-cycle Tv targets are outside this window.

Saved sigma is effective; total stress remains sigma-p*I. Q is the98 vertical second-difference RMS, distinct from alternating-X Uz/total-stress modes. All100 original material layers are evaluated at every new save. Material-centre pressure/stress/J span decomposition remains a small-strain diagnostic, not exact strain, mass, energy or force closure. Different pressure-round schemes are not assessed by a half/5Pa-equivalence gate.

## New outputs and visual layout

All new products use `tests/figures/upl_tpi_p3_window_review_r1.*`; check uses `tests/logs/upl_tpi_p3_window_review_r1.check.json`. Existing/partial outputs reject overwrite.

- history.csv: A1292 + B10/P2/P3 each1263 =5081 rows.
- layers.csv: new126300 material-layer rows plus real P2 physical-derived comparisons; no invented old n/rho fields. This large local derived table need not enter Git.
- profiles.csv: four series/two targets/100 layers =800 rows; old A/B10/P2 profiles reused directly.
- targets.csv: two new original-budget records, retained A/B10/P2 errors/failures and descriptive P3-minus-P2 changes.
- differences.csv:1263 true P3/P2 all-ID pressure RMS/max, periodic-minimum-image XYZ maximum and scalar differences.
- B10_scalar_differences.csv:1263 same-clock lightweight P3/B10 scalar pairs only, no per-ID XYZ/pressure claim.
- events.csv: six genuine selections per four series =24 rows.
- metrics.json: all new stress failures, unchanged target budgets, P2/staged failure context, full five-force/three-round evidence, late extrema and actual differences.
- Six PNGs: history, unfiltered startup, late, profiles, modes, differences. Axes use short human-readable labels with units; legends/reference explanations occupy a reserved band outside axes. P2/P3 mode heatmaps use every100-layer record and shared colour ranges, without clipping or smoothing. Old B10/A remain scalar/profile contexts, not fabricated field maps.

`passed/analysis_complete` only mean the analysis completed. Actual planned_budgets_passed/all_original_target_budgets_passed/all_new_post01_100Pa_guards_passed remain separate; physical_acceptance staysfalse, partial2s_only true and source_full_completed false. Passing a window does not admit a full solve or next numerical candidate.

## Independent offline admission

Entry: `D:/anaconda3/python.exe -B tests/support/upl_tpi_p3_window_review_r1.py --admission PATH --execution-authorized`.

Admission must be stage `upl_tpi_p3_window_review_r1.admission`, passed/offline_only true, job.tag exactly the actual P3 candidate. Inputs are deduplicated path/bytes/mtime_ns for the new script/note; imported P2 science/staged/causal/prior/P3native/P3runner/M0native/P2native files and relevant notes; original BASE_XML/plan note; new P3 run/read/review/completion/schema/IDs/physical/n/clock/history/ledger/plan; retained P2 scientific check/metrics/history/profiles/targets/events; retained P2 run/read/review/completion/schema/IDs/physical/clock. No old A/B10/P2 ledger, old staged table, raw BI4 or executable is consumed by this scientific action.

All consumed stats are checked at entry and seal, with no SHA scan. NumPy/BLAS threads are set to1 before numerical import. The root must independently admit analysis only after actual P3 native qualification, inspect the new PNG/CSV results and decide the next stage. This author draft never touches the active solver or starts any follow-on action.
