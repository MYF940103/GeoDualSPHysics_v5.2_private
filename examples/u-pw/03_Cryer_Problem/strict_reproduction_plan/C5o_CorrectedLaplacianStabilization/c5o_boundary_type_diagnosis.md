# C5o Corrected Laplacian Stabilization Note

Mode 8 remains a boundary-aware quadratic MLS Laplacian. C5o adds optional
limiters that act only on the recovered Laplacian before it is assigned to
`LapPorePress`.

- `CurvedDrainedCorrectedLaplacianLimiter=1` caps negative diffusion rates so
  the pressure-only update cannot drain more than a CFL-scaled local pressure
  gap in one pore-pressure time scale.
- `CurvedDrainedCorrectedLaplacianLimiter=3` blends the MLS Laplacian with the
  pre-existing material SPH Laplacian using `CurvedDrainedLimiterBlend`.
- `CurvedDrainedLimiterPreventNegative=1` can apply the positivity cap after a
  blend limiter.

No limiter clamps material pore pressure and no limiter counts dummy boundary
volume. `c5o_case_summary.csv` and `c5o_pressure_only_limiter_metrics.csv`
classify the pressure-only gate.
