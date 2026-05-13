# C5n Boundary Type Diagnosis

Mode 8 is a boundary-aware corrected Laplacian path, not a flux-only Robin
calibration. The manufactured-field audit separates two questions:

- `mode8_exact_boundary` tests whether the local quadratic MLS recovery can
  reproduce radial polynomial Laplacians when the boundary sample values are
  consistent with the manufactured field.
- `mode8_drained_zero_boundary` tests the strict drained constraint used by
  the pressure-only diffusion case, where the spherical surface value is
  prescribed as zero.

The pressure-only gate classifies the runtime behavior using the FV center,
volume-mean, surface-shell, flux-ratio, negative-pressure, and fallback metrics
written by `c5n_gate_metrics.csv`.

Result after the dp=0.008 pressure-only run:

- mode 8 is not a true stable Dirichlet realization;
- it is not merely weak Robin;
- it behaves as an over-strong, oscillatory boundary-constrained local operator;
- negative pressure and late apparent flux reversal occur;
- dynamic diffusion is worse than modes 4, 5, 6, and 7 despite the improved
  manufactured Laplacian consistency.
