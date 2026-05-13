# C5m Next Boundary Operator Plan

## Recommendation

C5m should be a CPU-only conservative multi-shell radial exchange prototype for
the strict Cryer drained sphere.

Do not implement it in C5l. This document only defines the next source task.

## Why This Route

C5l found that:

- the material-only `LapPorePress` operator preserves a constant field exactly;
- the same operator is acceptable in the deep interior for `u=r^2`;
- the largest error is near the curved drained surface;
- mode `6` can bring the global flux ratio close to `1` for `dp=0.010`, but
  the surface shell remains far above the FV reference;
- `dp=0.0065` worsens because the near-boundary cloud and boundary pair count
  are worse, even though the interior lattice is better.

This points to shell exchange, not just boundary flux strength.

## C5m Scope

Add one experimental CPU-only mode, or a guarded subroute of mode `6`, that
operates only when:

```text
PorePressureBoundaryOperator=3
PorePressureCurvedDrained=1
HydraulicElevationSource=0
```

Keep unchanged:

- PR governing equation;
- `FlexibleConfiningStress`;
- `SoilConstitutiveModel`;
- `HydraulicElevationSource`;
- modes `0` to `6` behavior unless the new mode is explicitly selected;
- GPU hard error for curved drained boundary.

## Numerical Target

Represent the near-boundary pressure field by radial shell storage:

```text
S_k = int_{shell k} u dV
```

and enforce finite-volume exchange:

```text
dS_k/dt = F_{k-1/2} - F_{k+1/2}
F_R = 4*pi*R^2 * D * (u_outer - 0) / (R - r_outer)
```

The update should convert shell exchange residuals into conservative
`LapPorePress` corrections. A sink in one shell must correspond to a source or
flux in the adjacent shell, except at the drained boundary where storage leaves
the domain.

## Minimal Prototype

1. Define fixed radial shells near the boundary, at least:
   - `0.6R-0.8R`;
   - `0.8R-0.9R`;
   - `0.9R-0.95R`;
   - `0.95R-R`;
   - include a controlled treatment for particles with generated radius
     slightly above `R`.
2. Compute volume-weighted shell means and volumes every PR update.
3. Compute FV target fluxes between shell means and at `R`.
4. Compare these target shell storage rates with the current SPH
   material-material contribution.
5. Apply conservative shell corrections so the near-boundary shells move
   toward the FV radial exchange balance.
6. Do not clamp material pressure.
7. Record shell populations, shell means, target fluxes, applied corrections,
   conservation residuals, and negative-pressure checks.

## Pressure-Only Gate

Run pressure-only diffusion first, not Cryer compression:

- `dp=0.010` and `dp=0.008`;
- compare against C5i FV radial reference;
- include modes `4`, `5`, and `6` as retained baselines;
- no `dp=0.0065` until the operator is stable.

Acceptance criteria:

- final surface shell mean much closer to FV `~85.9 Pa`;
- volume mean and center pressure not made worse;
- shell residual p95 lower than modes `4`, `5`, and `6`;
- no flux reversal;
- no strong negative pressure;
- `PorePressRate` maxAbs not worse than mode `6`;
- `code=0`, `excluded=0`, `Kplastic=0`.

## Deferred Alternatives

Corrected/MLS Laplacian near the curved boundary remains a useful later route,
but C5l suggests that local consistency alone is not enough. Improved sphere
generation and boundary selection should also wait until the shell-conservative
gate is clearer, because `dp=0.0065` already showed that resolution alone can
worsen the boundary cloud.

C6 and GPU work remain deferred until the pressure-only FV radial diffusion
gate passes.
