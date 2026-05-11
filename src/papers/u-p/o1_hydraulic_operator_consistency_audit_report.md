# O1-Revised Hydraulic Operator Consistency Audit

## Objective

This audit revisits the self-weight Scenario 2 discrepancy after A1/A2/P1 and B5:

- nominal Eq.(4) analytical reference: bottom excess relative RMSE about `7.59%`;
- calibrated effective reference: `cv_eff = 1.1175 cv_nominal`, bottom excess relative RMSE about `1.98%`;
- CPU/GPU `PorePressureBoundaryOperator=1` works, but long-run bottom excess RMSE is effectively unchanged relative to legacy mode 0.

The revised O1 question is:

> Since mDBC/cDBC multilayer boundary particles already exist mechanically, does the PR pore-pressure operator have an effective hydraulic Laplacian scaling or boundary-state participation issue that can explain `cv_eff/cv ~= 1.1175`?

No production source was modified. No DualSPHysics run was launched.

## Corrected Motivation

The issue should not be described as simple geometric kernel-support incompleteness. The model already contains multilayer mechanical boundary particles.

The sharper distinction is:

- **mechanical support exists** through mDBC/cDBC boundary particles;
- **hydraulic pore-pressure state participation does not exist** in the current PR production operator, because `LapPorePress`, `LapZ`, pressure feedback, and Shepard regularization filter neighbors with `CODE_IsFluid(...)`.

Therefore the current hydraulic operator is material-material only, unless `PorePressureBoundaryOperator=1` is enabled. That mode adds a material-adjacent virtual top/bottom contribution; it does not use mDBC/cDBC boundary particles.

## Source Audit Summary

See `o1_hydraulic_operator_source_audit.md`.

Main findings:

- mDBC/cDBC boundary correction reconstructs mechanical `velrhop`, EOS pressure/density, and normal-based ghost-node quantities.
- No `PorePress`, `LapPorePress`, or `LapZ` fields are reconstructed in the audited mDBC/cDBC correction code.
- CPU `ComputeHydroLapPorePressT()` and `ComputeHydroLapZT()` use `CODE_IsFluid` for both target and neighbor particles.
- GPU `KerComputeHydroPrDiagnostics()` does the same.
- GPU/CPU `PorePressureShepard` and `PorePressureAccelDiff` also use material-material interactions only.
- `PorePressureBoundaryOperator=1` is a separate top/bottom virtual contribution, not boundary-particle hydraulic quadrature.

## Paper Evidence for MLS / Boundary Hydraulic State

The converted paper text in `papers/u-p/converted/u_pw_paper_text.md` states that boundary particles are used for solid velocity/mechanical boundaries, and that Neumann pore-pressure conditions require additional treatment. It says the method adopts moving least squares from Chow et al. to extrapolate pore pressure from domain particles to boundary particles using a corrected kernel.

The local implementation notes in `papers/u-p/u_pw_sph_implementation_notes.md` also record that the paper uses MLS to extrapolate pore pressure to boundary particles.

So, MLS/boundary-particle hydraulic state is supported by the paper as a target method. It is not currently implemented in production.

## Standalone Diagnostic Setup

Directory:

`examples/u-pw/02_SelfWeight_Consolidation/experiments/Operator_Audit_O1_Revised/`

Script:

`hydraulic_operator_consistency_audit.py`

The diagnostic reconstructs the Scenario 2 centered 2-D material lattice:

- `Dp = 0.01 m`
- `h = 1.8 Dp = 0.018 m`
- support radius `2h = 0.036 m`
- material grid: `10 x 100 = 1000` particles
- `zmin = 0.005 m`, `zmax = 0.995 m`, `H = 0.99 m`
- Wendland 2-D kernel constants from `source/FunSphKernel.h`

Three operator models were tested:

| Model | Meaning |
| --- | --- |
| `M_material_only` | Current production PR material-material Laplacian. |
| `M_virtual_mode1` | Current `PorePressureBoundaryOperator=1` top/bottom virtual contribution. |
| `MB_ideal_boundary_particles` | Hypothetical material + boundary/ghost hydraulic particles with side/bottom Neumann and top Dirichlet excess state. |

Test fields:

- constant `u=1`
- linear `u=y`
- quadratic `u=y^2`
- eigenmodes `u_n(y)=cos(lambda_n y)`, `lambda_n=(2n+1)pi/(2H)`, `n=0..3`
- hydrostatic total pore pressure cancellation test

## Eigenmode Effective Laplacian Scaling

The fitted scale is defined by:

```text
LapSPH(u_n) ~= -s_n lambda_n^2 u_n
```

Full-domain scale results:

| n | M material-only | M virtual mode 1 | MB ideal hydraulic boundary particles |
| --- | ---: | ---: | ---: |
| 0 | `0.911970` | `0.912019` | `0.995287` |
| 1 | `0.911557` | `0.911606` | `0.994836` |
| 2 | `0.910732` | `0.910781` | `0.993936` |
| 3 | `0.909496` | `0.909545` | `0.992586` |

The A2/P1 calibrated time-factor scale is:

```text
cv_eff/cv_nominal = 1.1175
```

The current PR Laplacian does **not** show a `+12%` diffusion scale. In the full 2-D strip, the material-only operator is closer to `0.91`, i.e. slower than the analytical second derivative, not faster. The idealized hydraulic boundary-particle model is close to `0.995`, not `1.1175`.

## Boundary vs Interior

For mode `n=0`, material-only scales are:

| Region | Scale |
| --- | ---: |
| full | `0.911970` |
| interior excluding 1h from top/bottom | `0.925868` |
| interior excluding 2h from top/bottom | `0.926259` |
| interior excluding 3h from top/bottom | `0.926259` |
| interior excluding 2h from both x and z boundaries | `0.995287` |
| bottom layer | `0.691535` |

This decomposition says:

- the largest error in the production-like material-only 2-D strip comes from boundary participation, including lateral x truncation and top/bottom layers;
- the core interior, excluding lateral and vertical boundary regions, is already close to unity;
- the current `PorePressureBoundaryOperator=1` top/bottom virtual treatment barely changes the full-domain eigenmode scale, matching the B5 long-run observation that mode 1 and mode 0 are nearly identical.

## Hydrostatic Cancellation

The diagnostic also evaluated:

```text
LapPorePress/(rho_w g_h) + LapZ
```

for a linear hydrostatic total pressure field.

Maximum absolute residuals are at machine precision:

| Model | Full-domain max residual |
| --- | ---: |
| `M_material_only` | `6.94e-13` |
| `M_virtual_mode1` | `6.94e-13` |
| `MB_ideal_boundary_particles` | `9.20e-13` |

Thus the current pairwise `LapPorePress`/`LapZ` combination is not producing a detectable hydrostatic source bias in this idealized operator-level test.

## Hypothetical Correction Prototypes

Python-only prototypes were tested:

| Prototype | n=0 scale | n=0 RMSE |
| --- | ---: | ---: |
| raw material-only | `0.911970` | `11.5756` |
| scalar normalized by raw `s0` | `1.000000` | `12.6918` |
| ideal hydraulic boundary particles | `0.995287` | `0.00839` |
| 1-D quadratic MLS reconstruction | `0.999904` | `0.000171` |

Scalar normalization can force the global fitted scale to 1, but it does not fix the boundary/local error and increases full-domain RMSE for the tested eigenmodes. That makes scalar normalization a weak production candidate by itself.

The idealized boundary-particle model and the 1-D MLS prototype both bring eigenmode scaling close to unity and strongly reduce operator RMSE in the standalone test. This supports boundary-particle-aware hydraulic reconstruction as a plausible accuracy improvement, but it does not explain the observed faster coupled SPH time factor.

## Comparison With `cv_eff/cv = 1.1175`

The O1-revised operator-level result does not match the calibrated effective consolidation coefficient:

- current material-only `s_0 ~= 0.912`;
- idealized hydraulic boundary-particle `s_0 ~= 0.995`;
- Python MLS prototype `s_0 ~= 1.000`;
- calibrated long-run effective scale is `1.1175`.

Therefore the `~12%` faster apparent consolidation rate is unlikely to be caused by the PR Laplacian being too strong. It is more likely associated with coupled dynamics not present in the scalar eigenmode test:

1. volumetric coupling through `-DivVel`;
2. dynamic self-weight build-up and early pressure overshoot/undershoot;
3. explicit storage and effective compressibility mapping;
4. Shepard regularization;
5. hydromechanical damping and feedback;
6. particle motion / settlement changing the effective extraction state.

## MLS / Boundary Quadrature Value

Boundary-particle-aware hydraulic state and MLS are still useful for paper consistency because the original paper explicitly uses MLS to extrapolate pore pressure to boundary particles for Neumann pore-pressure conditions.

However, for this specific self-weight Scenario 2 discrepancy:

- boundary-aware MB improves the standalone spatial operator from `s_0 ~= 0.912` to `s_0 ~= 0.995`;
- it does not move the operator toward `1.1175`;
- B5 showed top/bottom virtual boundary mode 1 does not reduce long-run bottom excess RMSE;
- hydrostatic cancellation is already good in the current pairwise formulation.

So MLS/boundary quadrature may improve strict boundary formulation and local profiles, but it is unlikely to be the main fix for the 7.6% nominal bottom time-history discrepancy.

## Corrected-Gradient Status

Corrected-gradient PR operators should remain deferred as production features.

The O1-revised data point to hydraulic boundary-state participation as the better paper-consistency path than interior corrected-gradient production. The interior x/z core already has `s_0 ~= 0.995`, so a corrected interior operator is not the first target for Scenario 2.

## Recommended Next Step

Recommended:

1. Keep the calibrated-reference paper figure set as the current Scenario 2 validation line.
2. Keep `PorePressureBoundaryOperator=1` experimental, not default.
3. Do not pursue scalar global renormalization as production.
4. If stricter paper-equivalent boundaries are needed, design a CPU experimental MLS / boundary-particle hydraulic-state prototype that explicitly assigns `PorePress` / hydraulic head to boundary particles, with:
   - material-boundary pair participation;
   - side/bottom Neumann hydraulic-head consistency;
   - top Dirichlet excess pressure;
   - hydrostatic cancellation tests;
   - pressure-only eigenmode tests before any coupled long run.
5. Do not expect this MLS/boundary work alone to remove the `cv_eff/cv = 1.1175` apparent time-factor sensitivity; that should be investigated separately through coupled storage/damping/Shepard/DivVel diagnostics.

## Files Generated

CSV / JSON:

- `laplacian_consistency_polynomial_metrics.csv`
- `eigenmode_effective_scaling.csv`
- `hydrostatic_cancellation_metrics.csv`
- `hypothetical_correction_metrics.csv`
- `operator_audit_summary.json`

Figures:

- `laplacian_consistency_constant_linear_quadratic.svg/png`
- `eigenmode_effective_scaling_M_vs_MB.svg/png`
- `effective_cv_scale_vs_mode.svg/png`
- `boundary_vs_interior_operator_error.svg/png`
- `hydrostatic_cancellation_residual.svg/png`
- `hypothetical_correction_comparison.svg/png`
- `MLS_or_boundary_particle_effect_if_tested.svg/png`
