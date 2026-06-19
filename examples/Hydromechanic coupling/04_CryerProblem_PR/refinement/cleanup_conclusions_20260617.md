# Cryer refinement cleanup conclusions

Date: 2026-06-17

## Purpose

This note preserves the conclusions from temporary Cryer refinement tests before
cleaning the bulky intermediate output directories.

After cleanup, the retained result groups are:

1. `frdraw_test_20260617`
   - Particle generation mode comparison: regular `drawsphere` versus
     `setfrdrawmode auto="true"`.
2. `ud2_k1e4_full`
   - Completed `dp=0.003`, `k=1e-4 m/s` two-stage Cryer run to about `Tv=1`.

No `source/` code was modified by the cleanup.

## Preserved Full Result: k=1e-4

Path: `ud2_k1e4_full/dp003_k1e4_full`

Setup:

- Sphere radius: `R = 0.05 m`
- Resolution: `dp = 0.003 m`
- Load path: undrained spherical normal loading, then FreeSurface drainage
- Load: `q0 = 10000 Pa`
- Drainage-stage hydraulic conductivity: `k = 1e-4 m/s`
- Restart part: `Part_0041`
- Drainage time origin: `t = 0.082001 s`
- Final dimensionless time: `Tv = 0.9935`

Main findings:

- Center pressure at drainage opening: `p_center/q0 = 0.9409`.
- Simulated Cryer peak: `p_center/q0 = 1.0546` at `Tv = 0.0604`.
- Analytical value at the same sampled `Tv`: `1.0609`.
- Sampled analytical global peak: about `1.1054` at `Tv = 0.0381`.
- Later dissipation remains slower than the analytical curve.
- At `Tv = 0.9935`, simulation gives `p_center/q0 = 0.0052`; analytical value
  is `0.0004`.

Interpretation:

- Lowering permeability to `k=1e-4 m/s` suppresses the severe drainage-opening
  shock seen in `k=1e-3 m/s` tests and reproduces the Mandel-Cryer peak
  reasonably well.
- The remaining mismatch is mainly in the decay phase, indicating a
  boundary-layer or effective-diffusivity issue rather than only an initial
  shock issue.

## Preserved Result: Particle Generation Mode Test

Path: `frdraw_test_20260617`

Geometry-only conclusion:

- FrDraw makes the exterior sphere much cleaner:
  - `dp=0.003`: projected surface nearest-neighbor CV decreases from `0.4012`
    to `0.0149`.
  - `dp=0.005`: projected surface nearest-neighbor CV decreases from `0.2335`
    to `0.0179`.
  - outer radius error becomes nearly zero.

Dynamic probe conclusion:

- Directly replacing the full solid sphere with FrDraw is not suitable.
- For `dp=0.005`, `k=1e-4 m/s`, and `Tv ~= 0.25`:
  - regular generation: opening `p/q0 = 0.8434`, peak `p/q0 = 1.0207`,
    RMSE `0.1079`;
  - FrDraw generation: opening `p/q0 = 0.6101`, peak `p/q0 = 0.9339`,
    RMSE `0.1611`.

Interpretation:

- FrDraw improves the exterior surface but changes the interior particle
  distribution into shell-like radial layers with gaps.
- For Cryer, this is harmful because the problem needs a regular volumetric
  poroelastic sphere.
- The current `SphereNormal` load also applies `q0/(rho_mix*dp)` to tracked
  free-surface particles and is not an area-weighted pressure integration over
  the true curved surface.
- Direct FrDraw should not be used for the whole Cryer volume. A future hybrid
  approach would need a regular interior plus a controlled surface-only layer
  and area-weighted load/drainage.

## Cleaned Temporary Test Conclusions

The deleted directories contained exploratory tests of initialization, drainage
selection, ramp time, wait time, shell thickness, free-surface thresholds,
damping, permeability, and resolution. Their useful conclusions are:

- Direct uniform pore-pressure initialization was abandoned because it did not
  initialize the matching effective stress field and produced a mechanically
  unbalanced initial state.
- The better physical path is two-stage loading:
  1. no Cryer pore-pressure initialization,
  2. undrained spherical normal loading,
  3. wait until the center pressure and velocities are near steady,
  4. open drainage and treat that instant as analytical `t=0`.
- Extending undrained loading to about `0.078-0.082 s` improved the restart
  state, but center pressure still plateaued around `0.94 q0` for `dp=0.003`.
- With `k=1e-3 m/s`, opening FreeSurface drainage produced a strong early
  pressure drop and rebound. This persisted after reducing `PoreDtSafety` and
  adjusting `ShiftTFS`, so it was not mainly a pore time-step issue.
- Very high damping suppressed velocity but worsened the pressure response.
- The lower permeability `k=1e-4 m/s` was the first setting that followed the
  analytical Cryer peak well enough to justify a full-cycle run.
- SphereSurface drainage based on radius/thickness was sensitive to the
  stair-stepped sphere surface and missed or unevenly selected surface
  particles. FreeSurface drainage is currently the safer default for the
  regular volumetric sphere.

## Deleted Directories

The following temporary result directories were deleted after recording the
conclusions above:

- `dp0025_shell05_gpu_peak`
- `dp0030_shell05_gpu_peak`
- `dp00375_shell05_gpu_partial`
- `dp0050_shell05`
- `dp0050_shell05_gpu`
- `dp0050_shell05_gpu_alignedload`
- `dp00625_ramp001_d008`
- `dp00625_ramp004`
- `dp00625_shell05`
- `dp00625_uniform`
- `dp00625_wait0035`
- `dp0075_hold020`
- `dp0075_ramp001_d002`
- `dp0075_ramp001_d008`
- `dp0075_ramp003`
- `dp0075_shell025`
- `dp0075_shell05`
- `dp0075_shell05_k025e3_gpu`
- `dp0075_shell075`
- `dp0075_shell100`
- `dp0075_uniform`
- `dp0075_uniform_tfs12`
- `dp0075_uniform_tfs18`
- `dp0075_uniform_tfs22`
- `dp0075_wait0025`
- `dp0075_wait0035`
- `dp0075_wait0035_xi4e5`
- `dp0100_shell05`
- `dp0100_uniform`
- `ud2`
- `undrained_then_drained`

The old root-level files `refinement_summary.csv` and
`ud2_scan_conclusions_20260617.md` were also removed after their conclusions
were consolidated here.
