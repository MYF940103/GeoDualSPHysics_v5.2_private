# Lian 2023 Flexible Strip 2D Test Data

This directory keeps validation and historical diagnostic assets separate
from the release XML/BAT files in the case root. See [the case README](../README.md)
for the current entry point and protected results.

- `outputs/`: GenCase, DualSPHysics, raw `data/`, and VTK `particles/` output.
- `logs/`: GenCase, solver, PartVTK, and postprocess logs.
- `configs/`: generated variant XML files, if parameter sweeps are needed.
- `figures/`: cross-run comparison figures.
- `scripts/`: helper run and postprocess scripts.
- `notes/`: preserved conclusions from previous attempts.

Current formal case root files:

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

## Lian mode-4 mirror candidate (not yet accepted)

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
