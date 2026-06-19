# Cryer temporary-output cleanup conclusions

Date: 2026-06-18

This note preserves the useful conclusions from the recent Cryer exploratory
tests before deleting bulky generated outputs. Formal XML/BAT files, support
scripts, figures, and compact analysis notes are retained.

## Retained conclusions from refinement tests

The previous consolidated note is:

- `refinement/cleanup_conclusions_20260617.md`

Key points:

- Direct uniform pore-pressure initialization was abandoned because the
  corresponding 3D effective stress field was not initialized, producing an
  unbalanced initial state.
- The current physical path is two-stage loading:
  undrained spherical normal loading, then opening surface drainage and using
  that instant as the analytical time origin.
- For `dp=0.003`, the undrained Stage1 center pressure plateaued around
  `0.94 q0`, even after extending the undrained waiting time.
- `k=1e-3 m/s` caused a strong drainage-opening pressure drop and rebound.
- `k=1e-4 m/s` was the first setting that reproduced the Cryer peak reasonably
  well in the full-cycle run, although late dissipation remained slower than
  the analytical solution.
- FrDraw greatly improves the exterior surface regularity, but using it for
  the whole sphere creates shell-like internal layers and poorer dynamic
  pressure response than the regular volumetric sphere.
- FreeSurface drainage is safer than radius/thickness SphereSurface drainage
  for the current regular volumetric sphere.

## Retained conclusions from corrected Stage1 and damping tests

- Setting `HydroMechDrainage=0` in Stage1 successfully prevents the explicit
  drained pore-pressure boundary from being applied during undrained loading.
- `SoilDampingCoef=0.2` was too large and could freeze oscillations before the
  coupled pore-pressure/stress state equilibrated.
- `SoilDampingCoef=0.02` was used in the recent corrected Stage1 tests as a
  less aggressive damping choice, but it should not be considered fully
  optimized yet.
- FrDraw Stage1 looked geometrically cleaner in section plots than the normal
  generator, but its center pore pressure remained too low during Stage1.

## Retained conclusions from area-normalized SphereNormal load

The temporary SphereNormal load was changed from a thickness-based acceleration
to an area-normalized pressure discretization:

`a_i = -p0 * A_i * n_i / m_i`, with `A_i = 4*pi*R_eff^2/N_surface`.

For the Stage1 diagnostic:

- surface particles loaded: `3630`
- `R_eff = 0.05 m`
- `sum(A_i) = 0.0314159 m2`
- `A_i = 8.65453e-06 m2`
- full-load acceleration range: `[1526.37, 1526.37] m/s2`
- residual `|sum(A_i*n_i)|/sum(A_i) = 2.75e-4`

This indicates that the area-normalized load field is nearly balanced as a
whole.

## Retained conclusions from `HydroMechLoadAce` output

The external hydromechanical load acceleration is now available as
`HydroMechLoadAce` in particle VTK output when requested by PartVTK.

The short Stage1 diagnostic showed:

- total particles: `22483`
- `FSType=2/3` surface particles: `3630`
- particles with non-zero `HydroMechLoadAce`: `3630`
- loaded non-surface particles: `0`
- surface particles not loaded: `0`
- `dot(HydroMechLoadAce, radius)/(|HydroMechLoadAce||radius|)` mean: `-1.0`

Therefore, the current external load acceleration is applied to the expected
surface particles and points radially inward. The Stage1 low center pore
pressure is unlikely to be caused by a simple external-load direction error.

## Next diagnostic

The next test should compare Stage1 with `HydraulicConductivity=0` against a
nearly undrained but non-zero value such as `1e-8 m/s`.

Reason:

- In a strict undrained analytical process, no pore-water diffusion should
  occur.
- Numerically, however, setting `k=0` also removes any pore-pressure smoothing
  by the diffusion term. If the compression source term or stress response is
  spatially noisy, a very small `k` may reduce local discontinuities without
  behaving like a genuinely drained case.
- If `k=1e-8` materially improves the Stage1 pressure field while preserving
  the undrained center response, the issue is likely tied to noisy source-term
  accumulation or missing numerical regularization.
- If `k=1e-8` does not improve the center pressure, the main cause is more
  likely in the mechanical-to-pore-pressure coupling term, the deformation
  field, or the pore-pressure boundary/update logic rather than permeability.

## Deleted generated outputs

The following generated output directories were cleaned after recording these
conclusions:

- `area_load_diag_out`
- `CaseCryerProblem_PR_out`
- `area_load_test/out_loadace`
- `area_load_test/out_smoke`
- `refinement/corrected_stage1_20260617`
- `refinement/frdraw_test_20260617`
- `refinement/ud2_k1e4_full`
