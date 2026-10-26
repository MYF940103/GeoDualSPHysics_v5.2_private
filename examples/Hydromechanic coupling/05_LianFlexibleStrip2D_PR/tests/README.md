# Lian 2023 Flexible Strip 2D Test Data

## Latest supported-option review (2026-10-27)

`notes/lian_opt3_review_r1.md` records the completed 3-s gradient/damping study.
`figures/lian_opt3_review_r1_{paper,damping,history,boundary}.png` have matching
summary/history/native-field CSVs. All nine runs passed their runtime checks;
this is not new half-step, SPR/HG or paper-accuracy acceptance. The formal100-s
run remains stopped with its partial output protected. The next mixed-slip SPR
candidate and its plane-normal OFF control are separate from this review.

`notes/lian_spr_mix_r1.json` defines that separate candidate. Only the CPU/GPU
startup admission in `ConfigDomain` changes; existing per-particle vector
reflection and static convex plane checks are preserved. Twelve constant/affine
fixtures (CPU Debug/GPU Debug/GPU Release), a GPU Debug edge memcheck, and original
Lian SPR-OFF native regressions (CPU3/GPU31 frames,0ULP) have passed. The explicit
plane-normal OFF/ON3-s comparison is a new gated sequence, not physical release.
`logs/lian_spr_mix_r1.inputs_r2.json` corrects draft parameter comments only;
the original preparation/manufactured-test records remain unchanged.

This directory keeps validation and historical diagnostic assets separate
from the release XML/BAT files in the case root. See [the case README](../README.md)
for the current entry point and protected results.

- `outputs/`: GenCase, DualSPHysics, raw `data/`, and VTK `particles/` output.
- `logs/`: GenCase, solver, PartVTK, and postprocess logs.
- `configs/`: generated variant XML files, if parameter sweeps are needed.
- `figures/`: cross-run comparison figures.
- `scripts/`: helper run and postprocess scripts.
- `notes/`: preserved conclusions from previous attempts.

Retained 50-s formal case root files:

- `../CaseLianFlexibleStrip2D_PR_Def.xml`
- `../xCaseLianFlexibleStrip2D_PR_win64_GPU.bat`

Current retained setup:

- Domain: `20 m x 10 m`, `dp=0.1 m`.
- Strip footing: hard-coded Lian mode `HydroMechTopLoadMode=4`, `x=[0,1.25] m`, top surface `z=10 m`.
- Drainage: open top surface outside the strip starts after the 1 s ramp; the strip contact remains impermeable.
- Boundary: mDBC with a free-slip default and per-`mkbound` overrides:
  lateral walls (`mkbound=0`) are free-slip; the bottom (`mkbound=1`) is
  no-slip. The retained root `Run.out` reports both overrides as enabled.
- Current formal duration/time step: `50 s`, `DtFixed=1e-5 s`,
  `TimeOut=0.05 s`, and `SoilDampingCoef=0.04`.
- Pore-pressure regularization and density diffusion are disabled.

## Retained comparisons and historical status

- Preserve `../CaseLianFlexibleStrip2D_PR_out` as the retained full-run
  baseline, together with its native data and run logs.
- Preserve `outputs/CaseLianFlexibleStrip2D_PR_plasticoff_full_20260729_out`
  and its inputs/logs while reviewing the plasticity-off comparison.
  `notes/lian_plasticity_off_full_conclusion_20260730.md` records a
  byte-identical Part-file comparison; that historical statement is not a
  new duplicate-data verification or deletion instruction.
- `notes/TEST_CONCLUSIONS.md` describes an earlier abandoned setup, including
  the former mode-3 footprint. Later mode-4 tests resumed this case. Do not
  use that old note as the current configuration or file inventory.
- The late pore-pressure residual remained an open diagnostic issue in the
  retained notes. Finishing the 50 s run does not make this a fully validated
  benchmark, and the current case does not enable TPI.

## Current bounded review (2026-10-26)

- `logs/lian_drained_review_r1.check.json`: independently reviewed 61 native
  coarse/half pairs through 3 s. Maximum pressure RMS difference is
  `0.0111203 Pa`; top-material maximum displacement difference is
  `0.000012807 mm`. All active drained nodes (FSType 2 or 3, outside the
  current strip, all normal directions) have exactly zero pressure.
- `figures/lian_drained_review_r1_history.png` and `_fields.png` have matching
  CSV data. Current versus legacy final pressure RMS difference is
  `0.587581 Pa`; this is not an isolated stress-precision comparison or
  evidence that the late plateau is resolved. Legacy load telemetry is zero
  and must not be interpreted as a physically unloaded calculation.
- `notes/lian_late15_r1.json` specifies a fresh 15 s original mixed-slip,
  mode-4 strip diagnostic; its independent entry is
  `configs/xlian_late15_r1_win64_GPU.bat`. Only duration changes from the
  3 s coarse control. SPR/HG remain off. Its purpose is to cover the retained
  first contact/drainage change near 14.1 s, not to claim full-cycle acceptance.
- Formal root inputs and retained output remain unchanged. Formal closure
  still requires an independent actual run through the paper's 100 s endpoint,
  reviewed native comparisons, and corresponding formal PNG/CSV artifacts.

## Lian mode-4 mirror candidate and accepted 15-s contact repair

The current strict-footprint control first loses native node1744 near 12.40 s:
its x coordinate changes from a small positive value to -0.80 micrometres.
The node then loses its load and becomes drained; the observed total load
falls from approximately13000 to12000 N/m. A candidate mirrors the strip
predicate across the free-slip x=0 face (`abs(x)<=1.25`) on CPU and GPU.
This leaves the physical in-domain strip0..1.25m and its13-node quadrature
unchanged. It changes neither mDBC velocities nor pore/stress precision,
and does not normalize the original+4percent nodal-width bias. It is not
a general large-deformation contact law; short/half/late-window checks are
required before formal promotion. Prior source/programs and raw runs are
retained; candidate GPU programs are built in tests, not over the control.

Short review passed (`logs/lian_mirror_review_r1.check.json`): GPU Debug
memcheck0errors; .15s and3s independent half pairs pass the unchanged
5Pa/.005mm limits.3s maxima are0.0112047Pa/.0000128985mm. The same-dt
mirror/strict differences are not0ULP: max pressureRMS0.352672Pa and top
material displacement0.000656508mm through3s.13-node force and active
drainage pass. See the inspected history/startup/field PNGs and CSVs under
`figures/lian_mirror_review_r1_*` and `notes/lian_mirror_review_r1.json`.

The initial r1 GPU Debug loader failure (missing DLL runtime) remains frozen;
r2 adopted its successful CPU Debug and ran only the five missing GPU jobs.
No old worker was restarted. The next fresh15s pair is `lian_mirror15_r1`;
it alone can test the retained late switching window. No formal100s/FEM
or general-contact acceptance is claimed by this short checkpoint.

That fresh 15-s pair has now completed and was independently reviewed:
`logs/lian_mirror15_review_r1.check.json`,
`notes/lian_mirror15_review_r1.md`, and inspected
`figures/lian_mirror15_review_r1_{history,contact,fields}.png` with matching
history/pairs/prefix/fields CSVs. All 301 half pairs pass the original bounds
(0.0153762 Pa / 0.0000128985 mm maxima). Both 61-frame shared 3-s prefixes
are exact, all fields. Contact toggles and erroneous drainage disappear,
13 nodes retain 13000 N/m, and the old negative-pressure spikes disappear.
This admits one independent actual 100-s root release, not FEM accuracy.

The new root release XML/BAT are `../CaseLianFlexibleStrip2D_PR_release_Def.xml`
and `../xCaseLianFlexibleStrip2D_PR_release_win64_GPU.bat`.
`notes/lian_formal100_r1.json` defines the full run; its one-shot status is
`logs/lian_formal100_r1.status.json`. Retain the native-reader executable and
helper scripts used by `../support/postprocess_lian_release.py` during any
cleanup. Formal figures/CSVs go to `../figures`, not this diagnostic folder.

## Paper Fig10 first three times (2026-10-27)

`notes/lian_fig10_first3_r1.md` records the requested 0.5/1/3-s comparison.
Inspected `figures/lian_fig10_first3_r1_comparison.png` includes original
paper SPH/FEM crops, the new strict 15-s control and mirror coarse run;
`_half.png` compares mirror 10/5-us native states. Corresponding `_summary.csv`,
`_pairs.csv` and nine native-field CSVs share the same shallow filename tag.
Paper row limits are 0-5, 0-5, 0-1.75 kPa, not auto-scaled. At 3 s the mirror
peak is 2.11956 kPa and 9.024% of native nodes exceed that paper display
limit. Shape agreement is qualitative; fieldwise SPH/FEM accuracy is not
accepted. Contact repair does not remove this shared early-window mismatch.
No solver, formal inputs or active 100-s sequence were changed for this plot.

## Controlled 3-s option study (2026-10-27 user revision)

The user subsequently stopped the 100-s formal sequence. Its protected root
output contains 219 complete native frames through10.90001s, not100s;
`logs/lian_formal100_r1.user_stop.json`, `.user_stop_snapshot.json` and
`.user_stop_native.json` preserve ownership, the pre-stop status and native
endpoint evidence. Old worker and completion queue are retired.

`notes/lian_opt3_r1.json` and `scripts/lian_opt3_r1.py` define the first
supported one-option matrix: stress-rate-gradient correction1, damping off,
eta.02, eta.08, each .15-s smoke then3s at10us; reuse eta.04/grad0 baseline.
One CPU Debug2ms grad smoke precedes GPU jobs. Original side-free/bottom-no-slip
settings are checked in both XML and actual logs. Geometry/material/load/
permeability remain fixed. Result outputs, logs and CSVs use the same shallow
`lian_opt3_r1_*` filename tag. No new C++/CUDA change was made for this matrix.

SPR and HG are NOT claimed tested here: current SPR rejects mixed slip and
needs independently validated per-face normals/control; current HG neighbor
search is periodic-only. Do not bypass those guards or change boundary slip
to make them run. Those bounded compatibility tasks remain explicit, followed
by candidate half checks before any new long-run decision. Neither the paper
nor the current code is assumed automatically correct from color resemblance.
