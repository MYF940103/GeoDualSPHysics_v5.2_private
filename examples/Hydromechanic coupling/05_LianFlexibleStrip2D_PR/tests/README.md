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
