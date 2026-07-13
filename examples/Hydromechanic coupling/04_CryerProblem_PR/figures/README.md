# Cryer figures and data

This folder keeps only the current formal Cryer validation plots/data and the
parameter tests that still inform the release setup. Older exploratory images
and CSV files with settled conclusions were removed from this folder.

## Folder layout

- `formal_validation/`
  - Completed server run for `dp=0.0025`, `k=1e-5`, `nu=0.3`, center sample
    radius `r <= 1dp`.
  - Combined Poisson-ratio validation for `nu=0.1, 0.2, 0.3, 0.45`, plotted
    in the same normalized center-pore-pressure style as the u-pw reference.
  - High-resolution closed-ramp Poisson-ratio validation for `dp=0.002`,
    `k=1e-5`, `HydroMechTopLoadRampTime=0.0025 s`, and
    `HydroMechDrainageStartTime=0.0025 s`, with time shifted to the drainage
    start and center pressure sampled over `r <= 1dp`.
- `parameter_tests/`
  - `k=1e-4` versus `k=1e-5` early-window comparison.
  - `k=1e-5` short-window `dp=0.003, 0.0025, 0.002` convergence.
  - `SoilDampingCoef` sweep for the early oscillation window.
  - Ramp/drainage timing sweep with time aligned to the end of the load ramp.
- `diagnostics/`
  - Theory parameter check and `HydroMechLoadAce` radial integration
    diagnostics.

## Retained conclusions

- The formal `dp=0.0025`, `k=1e-5`, `nu=0.3` server result reproduces the
  Mandel-Cryer center-pressure trend and peak timing. The numerical peak is
  still slightly lower than the analytical peak, and late-time dissipation is
  slightly slower.
- The Poisson-ratio sweep reproduces the expected trend for `nu=0.1, 0.2,
  0.3`: lower Poisson ratio gives a higher center pore-pressure peak. For
  `nu=0.45`, the raw global maximum is affected by early startup oscillation,
  but the post-transient curve remains close to the analytical solution.
- Reducing hydraulic conductivity from `1e-4` to `1e-5` stretches the physical
  time scale and reduces early velocity/oscillation, but it does not by itself
  remove the remaining peak-amplitude deficit.
- Resolution refinement from `dp=0.003` to `0.002` monotonically raises the
  peak and reduces RMSE, so the remaining peak deficit is at least partly a
  spatial-resolution/SPH consistency effect.
- The formal `dp=0.002` closed-ramp Poisson-ratio sweep further reduces the
  peak deficit: at the theoretical peak time, the normalized deficit is about
  `-0.041`, `-0.034`, `-0.027`, and `-0.019` for `nu=0.1, 0.2, 0.3, 0.45`,
  respectively.
- `SoilDampingCoef=0.1` gave the best short-window RMSE/MAE among the tested
  damping values, while `0.05` remains a conservative lower-damping backup.
  The completed formal server run retained `0.02`.
- Finite ramp/drainage timing changes early velocity and oscillation but does
  not recover the missing peak. The current release path therefore keeps the
  one-stage drained setup with no ramp unless a quieter diagnostic run is
  specifically needed.
- Theory and load diagnostics showed that the analytical time scale is
  consistent with the implemented parameters, and the integrated
  `HydroMechLoadAce` is not under-applied. The peak deficit is therefore more
  plausibly tied to spatial distribution of the confinement term, drainage/free
  surface discretization, and resolution.

## Removed from this folder

The following superseded groups were deleted after their conclusions had been
captured in `refinement/notes/` and in the summary above:

- early `cryer_center_pressure.*` checks;
- old corrected-sweep and corrected-theory ramp figures from 2026-06-20 to
  2026-06-21;
- old `r0000`, `r0010`, `r0025`, `r0050`, `r010/r0115` exploratory ramp and
  drainage plots;
- early 2026-06-14 refinement figures based on older case assumptions;
- the local `cryer_k1e5_dp0025_full_20260622_*` full-run plots, superseded by
  the completed server full-run outputs;
- the single `cryer_k1e5_tv008_toutTv001_paper_axes.png`, superseded by the
  retained `k=1e-4` versus `k=1e-5` comparison and convergence results.

Historical notes remain under `../refinement/notes/`.
