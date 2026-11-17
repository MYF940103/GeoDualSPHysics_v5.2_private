# P2 bounded2s scientific adapter r1

Author-only draft. Neither this author stage nor this script launches a solver, reader, build, GenCase, VTK, queue or Git action. No physical analysis has been executed. P2 shorts have not yet been run and the P2 2s job is not admitted by writing this file.

New files: `tests/support/upl_tpi_p2_window_review_r1.py` and this note. Existing P1/M0 scripts, source, references, results and failures are untouched. All products use the new `upl_tpi_p2_window_review_r1` tag and refuse any existing/partial output.

## Reused scientific functions

The adapter imports the already reviewed P1 staged-window and causal modules without calling their main functions or changing module globals. It directly reuses:

- `causal.Admission` pin/read/table/finish semantics and original binary/stat/write/PNG helpers.
- `causal.references`: unchanged 512-mode unfitted M0/finite-Kw companion constants.
- `causal.describe`: unchanged pressure/settlement/total-stress/J/n/rho/100-layer diagnostics and every post-.1s100Pa gate.
- `staged.typed`, `staged.old_arrays` and `staged.differences`, including the original x-periodic minimum-image displacement expression.
- `staged.targets`: unchanged original pressure/top/bottom inequalities and original A target sampling. Only returned candidate labels and descriptive staged-context fields are adapted.
- `causal.events`: the same six actual-state selections for the new candidate.

P1's `load_new` requires a 44-column staged-load sidecar and its plots have hardcoded load-clock panels. Those are deliberately not called. The new loader verifies actual P2 provenance and then uses the same original common26/native formats. The new plot wrapper has no load-q panel or staged-load requirement. It does not duplicate the numerical companion/describe/budget implementations.

## Actual candidate, input qualification and clocks

The root admission explicitly chooses one completed P2 `job.tag`; it must match the fresh P2 tag syntax. The script consumes its genuine `.run.json`, `.native_p2_r1.json` and `.native_review_p2_r1.json`, and its `<tag>_native_p2_r1` directory. All must be actually passed and correctly bound, not renamed older P1 receipts.

Required run is Release/B/window2s: 199996 updates, 1263 frames, dt=`1.0000228881835938e-5 s`, actual scalar end=`2.00000577545594 s`, original drain-step1000 policy and 1159 post-open frames. Both reviewed and decoded job bind the actual run stat, plan, native path and solver output directory. Unique read invocation=1; native review must retain all22 original guards.

P2 review must actually cover 1263 saved four-phase intervals /1262 noninitial signed checks with zero added tolerance, both pressure rounds at all1263000 saved ID pairs, actual q2=validated p1 and zero added pressure tolerance. Original physical HG still has 2N force calls and N predictor/corrector updates; four complete force evaluations do not mean four HG updates.

Completion/common26/IDs/lattice declarations, binary shapes, all pressure/n/clock values, actual saved Step/dt/signed intervals, native history and original rho/J/n ledger are checked again for correct scientific association. This is not a second BI4 decode. The initial signed diagnostic is retained, not overwritten or interpreted as an empty-interval zero.

The original B10 and P2 must share all1263 actual time/Step/dt bits and every original material coordinate/ID. There is no nearest pairing, interpolation, rewritten final record or A/B/P2 cross-method 5Pa gate. The A curve keeps its own actual times, finite-Kw companion and original target gaps.

## Retained descriptive contexts

Original-source-clock B10 uses its already decoded physical/n/clock/ledger data, with the existing causal scientific history and qualifications. No solver or reference is repeated.

A uses only completed causal history/target/profile/metrics context; its large native binaries and ledger are not reloaded or rebuilt. A's post-.1s failures remain visible and do not exempt the new candidate.

The staged P1 comparison uses only its already completed check/metrics/history/targets/profiles/events. Its actual1263 lightweight time/step/dt associations must match P2. Its large native/ledger and 44-column loadclock CSV are not consumed. Thus staged scalar differences are genuinely descriptive; no staged per-ID pressure/XYZ difference or hidden-state equality is invented.

## Original numerical budgets, unchanged

At each covered target legacy Tv=.005 and .05:

1. Candidate layer-mean pressure-profile RMS error <= corresponding original A actual-time error +10Pa.
2. Absolute top-material settlement error <= original A + `.001*S_infinity_continuum_surface_mm` (the original .1 percentage point, approximately .003714285714mm).
3. Absolute bottom-material settlement error <=.005mm and <= original A +.002mm.

Every new saved state at `t>=.1-1e-7 s` must keep both all100-layer mean total sigma_zz maximum error and the top-two-layer gap <=100Pa. All startup and later states remain in the files; no late-only filtering hides failures. The inherited code applies the literal original comparisons, not rounded displayed limits.

The old A/B10/staged target failures are preserved. No looser new threshold, fitted time/load/radius, smoother, half chain or reference run is introduced. Later full-cycle Tv targets are outside this 2s coverage.

Saved six stresses are effective stress. Total stress remains saved_sigma minus p*I; shear is unchanged. Alternating-X Uz and all six alternating total-stress modes are retained for every100-layer history. Q is the RMS of 98 vertical layer second differences, not alternating-X amplitude. Pressure/stress/J strain-integral decompositions remain small-strain diagnostics, not exact fluid mass, energy, load balance or nonlinear consolidation theory.

P2 PorePressRate is the second-round scaled residual and is never used as actual dp/dt. The reviewer does not require residual shrinkage or reinterpret P2 as an exact implicit solve, literal paper LF or second-order integration.

## New products

Everything is written under `tests/figures/upl_tpi_p2_window_review_r1.*`, plus one new `tests/logs/upl_tpi_p2_window_review_r1.check.json`.

- `history.csv`: A1292 + B10/P1staged/P2 each1263 =5081 actual rows.
- `layers.csv`: all1263*100 new material layers, with same-clock original B10 descriptive fields and six total stresses; this large local derived table need not enter Git.
- `profiles.csv`: two targets/four series/100 layers =800 rows; existing A/staged profiles are reused, not refitted.
- `targets.csv`: two P2 original-budget rows, original A/B10 errors, and staged error differences without adding a new budget.
- `differences.csv`: 1263 actual native-ID pairs versus original B10, including pressure RMS/max and periodic-minimum-image XYZ maximum.
- `staged_differences.csv`: 1263 same-clock lightweight scalar pairs only; no per-ID XYZ/pressure claim.
- `events.csv`: six original actual-state selections per four series =24 rows.
- `metrics.json`: exact original budgets, every new100Pa failure, preserved context failures, full four-force/native/HG evidence, late1.5-2s extrema and descriptive comparisons.
- Six matching PNGs: history, unfiltered startup, late, profiles, modes and differences. Mode heatmaps show original B10/P2 all100 layers with shared color ranges, no clipping or smoothing. Staged mode amplitude is still shown in lightweight history/late curves, not fabricated as a field map.

Plot labels use short human-readable names and units, following the existing readable-differences replot. All six difference panels have explicit short labels; history/startup/late use a display-only label map. Legends and companion explanations occupy a reserved figure band above the axes, with short series names; CSV columns, values, numerical budgets and input bindings are unchanged. This is a static author correction, not a rendered-figure or analysis pass.

`passed/analysis_complete` on the check receipt means analysis completed. Physical budget results remain separate `planned_budgets_passed`, `all_original_target_budgets_passed` and `all_new_post01_100Pa_guards_passed`. A completed analysis with any failed budget remains a scientific failure of that budget, with `physical_acceptance=false`, `partial2s_only=true`, `source_full_completed=false`. It does not admit a full run or next solver.

## Independent offline admission and consumed inputs

Interface: `D:/anaconda3/python.exe -B tests/support/upl_tpi_p2_window_review_r1.py --admission PATH --execution-authorized`.

Admission: `stage=upl_tpi_p2_window_review_r1.admission`, `passed=true`, `offline_only=true`, `job={tag: actual_passed_P2_tag}`, deduplicated `inputs` containing actual path/bytes/mtime_ns. The required collection is:

- This script/note; actual imported staged/causal/prior/P2native/P2runner/M0native source modules and applicable notes; original BASE_XML and plan note.
- Actual P2 run/read/review, completion, columns/native_ids, physical.bin, soil_n.bin, clock.bin, native history.csv/ledger.csv and its original eight-column plan.
- Already qualified original B10 run/read/review/prior scientific check and native completion/schema/IDs/physical/n/clock/history/ledger/plan consumed by causal.load.
- Existing causal check/metrics/history/targets/profiles and completed staged check/metrics/history/targets/profiles/events.

Every consumed input uses the inherited stat admission and final unchanged check. No old SHA scan or raw BI4 read is added. NumPy/BLAS threads are set to1 before numerical import. No callable old main, native, build, solver, queue or Git action exists in the scientific path. After an actual separately admitted analysis, the root must inspect PNGs/CSVs and decide the next development stage.
