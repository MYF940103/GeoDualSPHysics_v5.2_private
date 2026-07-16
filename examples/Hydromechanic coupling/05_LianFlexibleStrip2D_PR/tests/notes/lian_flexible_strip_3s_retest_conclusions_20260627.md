# Lian 2023 Flexible Strip 2D - 3 s Retest Conclusions

## Purpose

Restart the Lian et al. (2023) 2-D flexible strip footing validation after the successful Yao 2025 2-D consolidation boundary/drainage fixes.

## Code And Case Setup

- Added `HydroMechTopLoadMode=4` / `LianFlexibleStrip` as a hard-coded benchmark footprint.
- Yao mode `3` remains `x=[-3,3] m`; Lian mode `4` uses `x=[0,1.25] m` on the `z=10 m` top surface.
- Drainage excludes the active strip footprint, so the strip contact remains impermeable while the open top drains after the ramp start time.
- Lian XML uses `20 m x 10 m`, `dp=0.1 m`, `E=20 MPa`, `nu=0.33`, `n=0.4`, `Kl=1 GPa`, `ksat=1e-3 m/s`, `q0=10 kPa`, `tL=1 s`, `eta_d=0.04`, no pore-pressure Shepard regularization, and no density/stress diffusion.
- The root GPU BAT writes results to `tests/outputs` and logs to `tests/logs`, and outputs `PartBound` plus `PartFluid`.

## Build Verification

- CPU Debug build passed.
- GPU Release build passed and produced `bin/windows/DualSPHysics5.2_GEO_win64.exe`.

## Run

- Output directory: `tests/outputs/CaseLianFlexibleStrip2D_PR_gpu3s_dp01_dt5e5_damp004_nodiffusion_lianstrip_out`.
- Time step: `DtFixed=5e-5 s`.
- This is an accelerated contour-screening run, not a final accuracy run. The original `DtFixed=1e-6 s` and a conservative `5e-6 s` run were too slow for interactive 3 s checking without TPI.
- Total runtime: `2153.686035 s`.
- Excluded particles: `0`.

## Key Diagnostics

At `t=0.5 s`:

- Loaded particles: `13`.
- Loaded x-range: `1.42e-05` to `1.19996 m`.
- Loaded outside strip: `0`.
- A EPWP: `2.531 kPa`; B EPWP: `1.568 kPa`.
- Max EPWP: `2.564 kPa`.

At `t=1.0 s`:

- Loaded particles: `13`.
- Loaded outside strip: `0`.
- A EPWP: `4.170 kPa`; B EPWP: `2.916 kPa`.
- Max EPWP: `4.208 kPa`.

At `t=3.0 s`:

- Open top abs max EPWP: `0.0 kPa`.
- Strip top EPWP range: `0.408` to `0.900 kPa`, so the strip contact is not being incorrectly drained.
- A EPWP: `0.896 kPa`; B EPWP: `0.897 kPa`.
- Max EPWP: `1.715 kPa`.

## Visual Assessment Against Fig. 10

- The cloud pattern is now qualitatively correct: EPWP develops under the left-top strip during ramp loading, peaks near `t=1 s`, and then dissipates from the open top while pressure spreads into the domain.
- The 3 s contour shows the drained top boundary and remaining internal/left-side EPWP, consistent with the Fig. 10 dissipation trend.
- The result should still be treated as preliminary because the timestep is accelerated and TPI is not implemented.

## Follow-Up

- For a publication-quality comparison, rerun with a smaller stable timestep such as `DtFixed=2e-5 s` or below, or implement/enable TPI.
- The current mDBC command path uses global free slip. This matches the Lian side-wall setting and the stable Yao setup, but does not independently enforce a fully fixed bottom and free-slip side walls.
