# A1 Analytical Reconstruction / 1D Reference Solver Audit

Date: 2026-05-12

## Objective

Audit whether the analytical reconstruction used for the GPU G9/G9b/B5
self-weight Scenario 2 comparisons is exactly consistent with the current
u-pw PR implementation, and identify the most likely source of the remaining
approximately 8% bottom excess pressure discrepancy.

No source code was modified. No DualSPHysics CPU/GPU long run was executed.
Only retained result CSVs, retained figures, and a standalone Python 1D
finite-difference reference solver were used.

## Current B5 Conclusion Recap

B4/B5 showed that `PorePressureBoundaryOperator=1` was ported successfully to
GPU and is stable:

- CPU/GPU `mode=1` pressure-field parity passed for short tests.
- GPU B5 `mode=1`, `xi=0.05`, `TimeMax=3.6 s` finished with `code=0` and
  `excluded=0`.
- Bottom excess RMSE against the previous analytical reconstruction was
  effectively unchanged:
  - `mode=0`, `xi=0.05`: `550.17 Pa`, relative RMSE `0.07594`;
  - `mode=1`, `xi=0.05`: `550.18 Pa`, relative RMSE `0.07594`.

Therefore the discrepancy should not be primarily attributed to the legacy
post-update layer correction.

## Output Files

Audit directory:

```text
examples/u-pw/02_SelfWeight_Consolidation/experiments/Analytical_Audit_A1/
```

Generated files:

- `run_a1_analytical_audit.py`
- `analytical_parameter_audit.csv`
- `time_shift_sensitivity_metrics.csv`
- `fd_reference_metrics.csv`
- `cv_sensitivity_metrics.csv`
- `initial_condition_comparison.csv`
- `analytical_vs_fd_vs_gpu_bottom_excess.csv`
- `analytical_vs_fd_vs_gpu_profiles.csv`

Figures:

- `figures/initial_excess_profile_comparison.svg/png`
- `figures/bottom_excess_analytical_vs_fd_vs_gpu.svg/png`
- `figures/excess_profiles_analytical_vs_fd_vs_gpu.svg/png`
- `figures/time_shift_sensitivity.svg/png`
- `figures/fd_reference_variants.svg/png`
- `figures/cv_sensitivity.svg/png`
- `figures/error_source_ranking.svg/png`

## Analytical Formula Source

The reconstruction follows the local Supporting Information notes:

- `src/papers/u-p/supporting_information_implementation_notes.md`, Section 3.
- Initial undrained self-weight response:

```text
u0(z) = [(Kw/n) rho g (H-z)] / [M + Kw/n]
M = K + 4G/3
```

- Dissipation basis for a top-drained / bottom-no-flux 1D column:

```text
u(z,t) = sum A_n cos(lambda_n z) exp(-lambda_n^2 cv t)
lambda_n = (2n+1) pi / (2H)
```

For Scenario 2, total pore pressure is reconstructed as:

```text
p_total(z,t) = p_hydro(z) + u(z,t)
```

where `u` is excess pore pressure.

## Governing Equation Consistency

The code PR update is:

```text
PorePressRate = Kw/n * (
    -DivVel
    + k/(rho_w*g_h) * LapPorePress
    + k * LapZ
)
```

The analytical reconstruction is not this equation in raw particle form. It is
the reduced 1D consolidation equation obtained after assuming quasi-static 1D
mechanical storage:

```text
du/dt = cv d2u/dz2
```

with top drained `u=0` and bottom no-flux `du/dz=0`.

Consistency audit:

| Code term | Analytical treatment | Status |
|---|---|---|
| `-DivVel` | eliminated into effective constrained modulus/storage | assumption, not exact dynamic parity |
| `k/(rho_w*g_h) LapPorePress` | included through `cv` after hydrostatic/excess split | consistent only after storage reduction |
| `k LapZ` | cancels hydrostatic component in exact continuum split | numerically approximate in SPH |
| hydrostatic reference | added back for total pressure | consistent |
| top drained | `u(H)=0` | consistent as ideal boundary |
| bottom no-flux | `du/dz(0)=0` / head no-flux | consistent as ideal boundary |

The direct PR hydraulic diffusivity before mechanical storage elimination is:

```text
(Kw/n) * k/(rho_w*g) = 67.96 m2/s
```

whereas the analytical reconstruction uses:

```text
cv = k*M/(rho_w*g) = 0.27445 m2/s
```

This confirms that the analytical curve is not a pressure-only PR hydraulic
operator reference. It is a coupled/quasi-static 1D consolidation reference.
Any difference in the effective `DivVel` response, damping, Shepard smoothing,
or dynamic storage will change the apparent `cv`.

## Parameter Mapping Audit

See `analytical_parameter_audit.csv`.

Important findings:

- The comparison uses `H=0.9900000001 m`, from material particle centers
  `z=0.005..0.995 m`, not the nominal geometric `H=1.0 m`.
- `n`, `k`, `Kw`, `rho_w`, `g`, `E`, and `nu` are consistent between the XML
  setup and the reconstruction.
- The finite-`Kw` storage correction gives
  `cv=0.27334 m2/s`, only about `0.4%` below the current `cv`; it does not
  explain the 8% discrepancy.
- The analytical initial excess state is not a saved solver state. Saved
  `Part_0000` is the pre-undrained hydrostatic initialization with
  `ExcessPorePress=0`.
- Bottom GPU values are bottom-layer means, while the analytical value is the
  point value at `z/H=0`. This is a secondary approximation.

## Time-Origin Audit

Tested analytical time origins:

- no time shift: `tau=t`;
- physical drainage shift: `tau=max(t-0.002,0)`;
- diagnostic best-fit offset over `[-0.02, 0.05] s`.

For GPU `mode=0`, `xi=0.05` bottom excess:

| Time origin | RMSE | Relative RMSE |
|---|---:|---:|
| no shift | `540.20 Pa` | `0.07468` |
| drainage shift `0.002 s` | `550.17 Pa` | `0.07594` |
| best-fit diagnostic offset `-0.020 s` | `447.00 Pa` | `0.06279` |

For GPU `mode=1`, `xi=0.05`:

| Time origin | RMSE | Relative RMSE |
|---|---:|---:|
| no shift | `540.21 Pa` | `0.07468` |
| drainage shift `0.002 s` | `550.18 Pa` | `0.07594` |
| best-fit diagnostic offset `-0.020 s` | `447.01 Pa` | `0.06279` |

The physical `0.002 s` drainage shift is internally consistent with the XML,
but it is not the best numerical fit. A negative best-fit offset means the GPU
curve decays faster than the reconstructed analytical curve. This is a
diagnostic signal, not a recommended physical clock.

## Initial Condition Audit

The analytical initial bottom excess at drainage activation is about:

```text
u0(bottom) = 20.31 kPa
```

But the saved solver frame at `t=0` is hydrostatic:

```text
ExcessPorePress = 0
```

The first retained post-drainage frame is `t=0.1 s`. At the bottom:

| Quantity | Value |
|---|---:|
| analytical `u(0,0.1s)` | `16.52 kPa` |
| GPU `mode=0`, `xi=0.05`, approximate | `16.09 kPa` |
| GPU `mode=1`, `xi=0.05` | `15.89 kPa` |

Thus the first comparable retained frame is already lower than the analytical
reconstruction by several hundred pascals, which is the same order as the
long-run bottom RMSE. The actual state at `t=0.002 s` is not saved in the G9b
or B5 long runs, so the generated undrained profile cannot be directly compared
against Eq. (4) in those retained datasets.

## Standalone 1D FD Reference Solver

Implemented a standalone implicit finite-volume 1D solver for:

```text
u_t = cv u_zz
u(H,t) = 0
u_z(0,t) = 0
u(z,0) = u0(z)
```

Variants:

1. homogeneous diffusion with `cv=k*M/(rho_w*g)` and `t-0.002`;
2. homogeneous diffusion with finite-`Kw` storage-corrected `cv`;
3. direct PR hydraulic-only coefficient `(Kw/n)k/(rho_w*g)`;
4. no time shift.

Key metrics against GPU `mode=0`, `xi=0.05` bottom excess:

| Reference | RMSE | Relative RMSE |
|---|---:|---:|
| analytical series, `cv=Mk/(rho_wg)`, shift `0.002` | `550.17 Pa` | `0.07594` |
| FD same `cv`, shift `0.002` | `551.19 Pa` | `0.07607` |
| FD finite-`Kw` storage-corrected `cv` | `570.41 Pa` | `0.07855` |
| FD direct PR hydraulic-only coefficient | `6750.03 Pa` | huge / not comparable |
| FD same `cv`, no shift | `541.22 Pa` | `0.07481` |

The FD homogeneous solver matches the analytical series closely. Therefore,
the implementation of the series is not the main issue.

An additional `cv` sensitivity diagnostic shows that scaling the analytical
`cv` by about `1.12` reduces GPU `mode=0`, `xi=0.05` bottom-excess RMSE to:

```text
136.28 Pa, relative RMSE 0.01997
```

This is the strongest signal in the audit: the GPU curve behaves like a
slightly faster effective consolidation process than the current analytical
time-factor mapping.

## GPU Mode 0 / Mode 1 vs Analytical vs FD

Mode 0 and mode 1 are nearly indistinguishable in bottom time-series error:

| Line | Bottom excess RMSE vs analytical |
|---|---:|
| GPU `mode=0`, `xi=0.05` | `550.17 Pa` |
| GPU `mode=1`, `xi=0.05` | `550.18 Pa` |

The FD homogeneous reference is also almost identical to the analytical series,
so the 8% discrepancy is not caused by analytical-series implementation error.

Mode 1 remains stable and useful for parity testing, but the current
material-adjacent ghost contribution does not improve the analytical
comparison.

## Error Source Ranking

Based on the audits and metrics:

1. **Effective consolidation coefficient / time-factor mapping.**
   A `cv` scale of about `1.12` reduces relative RMSE from about `7.6%` to
   about `2.0%`. This is the largest quantitative improvement.

2. **Unobserved dynamic initial condition at drainage activation.**
   The analytical initial profile assumes an instant undrained Eq. (4) state at
   `t=0.002 s`, but the retained long-run data do not save that state. The first
   saved comparable frame already contains a several-hundred-pascal offset.

3. **Coupled mechanical dynamics, damping, and Shepard smoothing.**
   The analytical curve assumes quasi-static storage elimination. The code
   solves the explicit coupled PR/mechanics system with damping and periodic
   Shepard pressure regularization.

4. **SPH operator and layer-averaging discretization.**
   Bottom comparisons use a material-layer mean and SPH operators, whereas the
   analytical curve is pointwise continuum.

5. **Boundary condition implementation.**
   B4/B5 show that changing from legacy layer correction to the current
   operator-level material ghost does not reduce the bottom time-series RMSE.
   Boundary treatment is still relevant for strict reproduction, but it is not
   the dominant source of the current 8% bottom excess discrepancy.

6. **Finite-`Kw` storage correction.**
   This changes `cv` by less than 0.5% and slightly worsens the current fit.

## Answers to the A1 Questions

1. **Is the analytical reconstruction fully identical to the code PR equation?**

   No. It is consistent with a reduced quasi-static 1D consolidation equation,
   not with the raw explicit PR update including `DivVel`, damping, Shepard,
   moving particle positions, and SPH operator details.

2. **Most likely source of the 8% discrepancy?**

   Effective consolidation time factor / diffusivity mapping, followed by the
   unobserved dynamic initial state at drainage activation. A 12% larger
   effective `cv` explains most of the bottom time-series discrepancy.

3. **Does time shift significantly affect the error?**

   A physical `0.002 s` shift versus no shift changes relative RMSE only from
   `0.07594` to `0.07468`. A diagnostic negative offset improves it to
   `0.06279`, but this is not physically acceptable by itself. Time origin is
   not the main fix.

4. **Is the FD reference closer to GPU or analytical?**

   The homogeneous FD reference is essentially the analytical series. It is not
   closer to GPU unless the effective `cv` is increased. This confirms that the
   analytical-series implementation is sound, but its coefficient/initial-state
   assumptions are not fully aligned with the dynamic SPH run.

5. **Should `mode=1` boundary remain?**

   Yes, but as optional experimental infrastructure. It should not become the
   default production path based on current evidence.

6. **Is more complete MLS / boundary quadrature still needed?**

   It may still be needed for strict boundary theory, Cryer, and non-1D cases,
   but B5 shows it is unlikely to be the first-order explanation of the current
   Scenario 2 bottom excess discrepancy.

7. **Should corrected-gradient PR production be enabled now?**

   No. The discrepancy is better explained by effective 1D reference mapping
   and initial/dynamic coupling assumptions. Corrected-gradient remains
   deferred.

## Recommended Next Step

Before modifying more boundary/source code, run a targeted **reference
calibration audit**:

1. Save an output exactly at or just after `T_undrained=0.002 s` in a short
   self-weight run.
2. Compare that generated excess profile directly with Eq. (4).
3. Recompute analytical curves using:
   - the measured generated initial excess profile;
   - an effective `cv` fitted only from early pressure-only/equation-level
     behavior;
   - the same bottom-layer averaging used in the SPH metrics.

Only if that calibrated reference still shows a large discrepancy should the
next code-facing step be a stronger MLS/boundary quadrature operator.
