# P1 A/B/C startup science review: author-only offline script

2026-11-17, Asia/Tokyo. New assets are this note and
`tests/support/upl_tpi_cpu_startup_review_r1.py` only. The author has not imported
or executed this analysis. Root must read the entire script/note and independently
admit its one offline execution. No solver, reader, build, old analysis, hash,
Git, worker, clock rewrite or automatic next physical job is included.

## Required data and independent qualification

Only the three exact startup jobs are admitted:

- `upl_tpi_cpu_ReleaseCPU_A_startup015_r1`;
- `upl_tpi_cpu_ReleaseCPU_B_startup015_r1`;
- `upl_tpi_cpu_ReleaseCPU_C_startup015_r1`.

Each job must already have a passed original `.native_review_r1.json` from
`upl_tpi_cpu_native_r1.review`, matching the actual ReleaseCPU scheme and
startup015 window. This script reads existing exports, never invokes that
reviewer or reader. Missing or failed C is reported explicitly and prevents
publication of an A/B-only comparison disguised as an A/B/C pass. A passed
reader or an exit0 alone is insufficient. If any input/analysis fails, a new
failed receipt preserves the actual failure and any new partial artifacts;
neither original data nor old results are overwritten or rerun.

The existing native output directory is `<tag>_native_r1`. Consumed leaves are
`completion.json`, `columns.csv`, `native_ids.csv`, `physical.bin`, `soil_n.bin`,
`clock.bin`, `history.csv` and `ledger.csv`, plus the original actual plan path
bound in that reviewed job, and its owned output directory's original
semicolon-delimited `Run.csv`. No BI4, all-node source snapshot, executable or
hash scan is needed here. Original fixed particles and all 22 typed arrays
remain qualified by the passed original native review/completion; the science
script does not fabricate fixed values from its soil-only common26 export.

Counts remain 344 frames, 1040 original native IDs (1000 soil and40 fixed),
24000 updates, original dt6.250143051147461e-6s and actual scalar end
.1500034332275618s. It independently replays scalar `+=dt` only to check
already-saved clocks against the bound plan and existing clock payloads; it
never substitutes `n*dt`, alters a saved time or interprets Step as one-based.
The original initial signed diagnostic is retained. All343 noninitial signed
intervals must be nonempty and <=1e-14 without abs or a relaxed bound. Event
completed1600 is pre-open, part117; part118 has completed1601. The original226
post-open frames and2260 true drained checks remain required.

The existing physical binary header must remain `(1000,26,344)`. Its exact
schema is `case02_common26_col21_ExcessPorePress_NOT_wave26`; column21 must
never be relabelled PosDiv. Native density is read from the original density
ledger, with original IDs/time/J/n checked, and not substituted by legacy
`Rhop` or an independently evolved density. All three schemes must have
byte-identical actual time payloads, completed-step tables and initial
material coordinates before cross comparisons. No matching by nominal time
or interpolation is permitted.

## Observables and original safety

Original material IDs establish the complete100-layer/10-column lattice.
Every startup state is retained, including loading, opening and negative
pressure transients. Downward settlement is `-1000*(z-z0)`; top10/bottom10 are
the original z0=.995/.005m layers. Reclassification by current z is forbidden.
Total stress is effective stress minus pI, with the six native double stress
components retained. The script reports native pressure mean/RMS/min/max,
J-weighted pressure mean, material settlements, all six total-stress means,
Q, speed and native J/n/rho ranges.

The definitions of total stress and alternating modes are independently
transcribed from `support/upl_bigstep_full_review_r1.py:337-366`. That full
review itself did not implement a separate100Pa guard. The original guard
definitions are in `support/gpu_coupled_compare.py:61-75` and independently
visible in `support/hourglass_check.py:422-429`:

`layer_total[z] = mean_over_original_X(sigma_zz-p)`;

`max_layer_total_error = max_z(abs(layer_total[z]+10000))`;

`top_gap = abs(layer_total[99]-layer_total[98])`.

At every original saved time `t>=.1-1e-7`, both values must be <=100Pa.
The original start predicate, target q0 and limits are unchanged; the script
does not replace the maximum by an RMS or remove top layers. Q is the RMS of
the second difference of the100 layer totals; it includes physical curvature
and is not a pure numerical hourglass amplitude. Failure is retained with
scheme, actual time, completed step and worst layer. Valid native data are
still plotted and tabulated if this scientific guard fails; the final receipt
and process result then remain failed (return2), with C never omitted.

The alternating Uz mode is exactly the signed original-column projection:
subtract each layer's X mean, multiply even/odd columns by +1/-1, then mean.
It uses upward Uz, so it has the opposite sign of downward settlement. Every
one of100 layers at every344 times is kept. Total sigma_zz has the analogous
mode. The full tensor alternating RMS is additionally recorded in history.
No smoothing, clipping, mode threshold, new force acceptance or half test is
introduced. Existing native load telemetry remains saved-state evidence;
this analysis does not turn it into an independent same-force-stage load
certificate.

The three original Run.csv summaries must each contain one CPU/Single-core row,
24000 steps and344 native frames. Per-scheme metrics preserve their actual
TSimul/TTotal (including original decimal tokens), TSeg display value and
24000/TSimul steps per second. These are observed, nonisolated and instrumented
runtimes, not a controlled benchmark or an isolated solver-kernel cost. B/C
include their extra endpoint work and pressure sidecar overhead. Rounded
Run.csv PhysicalTime is retained as display text only and never supplies or
replaces any physical clock, sampling alignment or theory time.

## Qualified finite-Kw/M0 companion curves

Reference constants come from the actual frozen
`configs/upl_bigstep_c625_r1.xml`: E2e6Pa, nu.3, k1e-4m/s, rho_w1000kg/m3,
Kw2e8Pa, n0.3, q0=10000Pa and the original ramp/drain event
.010000228881835938s. Primary H=1m, reference g=9.81m/s2 and512 Fourier modes
are the exact existing companion choices, not fitted to A, B or C. Native
ledger n/k may reflect float XML storage; the reference retains the original
XML physical values, as the prior full review did.

A uses the finite-Kw quasi-static companion: amplitude Bq0 and diffusivity
BCv, where `B=1/(1+n0*M/Kw)` and `Cv=k*M/(rho_w*g)`. B and C share the same
M0 companion with amplitude q0 and diffusivity Cv. They do not get different
theory curves. Companion pressure and settlement are evaluated at the actual
saved times and original material z0, only where `t>=tD`. The loading history
before tD is kept but no quasi-static reference is invented there.

These are unfitted ideal closed-loading/single-top-drainage, small-strain,
constant-coefficient quasi-static companions. They are not exact solutions
for the finite ramp, normalized kernel band, startup inertia, dynamic
solid/fluid acceleration, evolving J/n or wall discretization. Profile RMS
and settlement differences relative to them are descriptive, not a startup
theory-accuracy gate or physical release. The existing H=.995 sensitivity is
not selected or silently refitted. Original native `PorePressRate` remains
the legacy Kw/n-scaled endpoint residual, not B/C's actual dp/dt.

Cross A/B/C data use matched actual times and material IDs. Pairwise pressure
RMS and material XYZ maximum differences are reported without a5Pa/.005mm
half or cross-model equality test. X differences use the original .1m
periodic minimum image; no spatial particle matching is performed.

## New products and one execution contract

Only `tests/figures/upl_tpi_cpu_startup_review_r1.*` is created:

- `history.csv`: all344 startup frames per scheme, condensed observables;
- `profiles.csv`:100 material layers at the five nearest actual common
  frames requested by0/.01/.025/.075/.15s, with signed gaps recorded;
- `modes.csv`: all100 signed layer Uz/total-sigma-zz modes at all344 frames
  per scheme, not another1000-node field dump;
- `cross.csv`: all344 matched-time A-B/A-C/B-C descriptive comparisons;
- `metrics.json`: native/scientific scope, extrema, final values, original
  observed runtime/steps-per-second and actual safety failures, without a new
  theory-accuracy threshold;
- `history.png`: pressure, material top/bottom settlement, total stress/Q,
  native J/n/rho and speed, with all startup samples;
- `profiles.png`: fixed-layer pressure/settlement/total-compression profiles,
  actual time captions and the qualified companions; legends use the final
  valid post-drainage column, including both black companion curves;
- `modes.png`:100-layer mode maps and RMS/max histories. Each map's symmetric
  range is declared by its own colorbar; ranges are not shared between
  schemes, and numeric magnitude comparisons belong to their reported values.

There is no late1.5-2s mode or full2Tv conclusion from this .15s window.
All CSV/JSON and PNG writes require absent destinations, including binary
exclusive file handles for PNGs. A new receipt is written to
`logs/upl_tpi_cpu_startup_review_r1.check.json`. Existing success/failure/partial
paths make any subsequent invocation refuse overwrite.

Root admission is a JSON with `stage="upl_tpi_cpu_startup_review_r1.admission"`,
`passed=true`, `offline_only=true` and `inputs=[{path,bytes,mtime_ns}, ...]`.
Inputs must include this script/note, the XML, the two formula-definition
source files named by `DEFINITIONS`, all three native-review receipts and
every consumed native leaf/actual plan and the three original owned Run.csv
files. Only these necessary input stats
are checked; no contents are hashed. The script imports NumPy/Matplotlib
normally but imports or calls no old analysis/build/solver helper.

After complete root read, the single command from case02 root is:

`D:/anaconda3/python.exe -X utf8 -B tests/support/upl_tpi_cpu_startup_review_r1.py --execution-authorized --admission ROOT_JSON`

`passed` means all requested native/clock/schema qualifications and the
unchanged post-.1s safety checks passed, not full physical accuracy, half-step,
complete2Tv, restart, GPU or formal acceptance. No follow-up is launched.
