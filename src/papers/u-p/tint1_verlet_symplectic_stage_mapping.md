# TINT1 Verlet/Symplectic Stage Mapping

Date: 2026-05-14

## Objective

This note maps DualSPHysics mechanical time staging and compares it with the
current pore-pressure scalar update. The goal is to decide whether pore
pressure is being treated as a density-like scalar, a stress-like internal
variable, or an operator-split hydraulic state.

## Verlet Mechanical Staging

`JSphCpu::ComputeVerlet()` starts at `source/JSphCpu.cpp:6640`.

The mechanical step calls `ComputeVerletVarsFluid()` at
`source/JSphCpu.cpp:6534`. For material particles it:

- computes density from `velrhop2.w + dt2 * Arc`;
- uses `Acec + gravity` for velocity and displacement;
- advances stress trial values from `sigma2 + Rsigmac * dt2`;
- calls `ApplySoilConstitutiveModelCpu()` before writing `Sigmac`;
- updates position and `Velrhop`;
- swaps current and previous arrays at the end of `ComputeVerlet()`.

Verlet alternates between a `2 dt` update and a `dt` reset step through
`VerletStep`. Stress follows that same staging through `SigmaM1c`, `Sigmac`,
and `Rsigmac`.

Pore pressure does not have an analogous previous-step array. It is updated
directly in place before `ComputeVerlet()`:

```text
Interaction_Forces -> PorePressRate^n -> PorePress += rate * dt -> ComputeVerlet
```

That makes the pore-pressure scalar neither Verlet-centered nor stress-like.
It is an explicit split state.

## Symplectic Mechanical Staging

`JSphCpu::ComputeSymplecticPre()` starts at `source/JSphCpu.cpp:6666`.
It stores previous arrays in `PosPrec`, `VelrhopPrec`, and `SigmaPrec`, then
advances material particles by `0.5 dt`:

- `Velrhopc` becomes the predicted half-step velocity/density;
- `Sigmac` becomes a predicted half-step stress;
- `Posc` becomes a predicted half-step position.

`JSphCpu::ComputeSymplecticCorr()` starts at `source/JSphCpu.cpp:6799`.
It computes the corrected density, velocity, stress, and displacement from the
stored `*Prec` arrays and the corrector acceleration/stress rate.

The pore-pressure update is not split into predictor and corrector parts:

```text
predictor Interaction_Forces -> ComputeSymplecticPre
corrector Interaction_Forces -> PorePress += rate * dt -> ComputeSymplecticCorr
```

The corrector pressure rate uses predicted mechanical variables, but the
pressure itself is old. There is no `PorePressPrec`, no half-step
`PorePress`, and no corrected pressure-rate recomputation.

## Density, Stress, and Acceleration Comparisons

| State | Verlet treatment | Symplectic treatment | Pore-pressure treatment |
|---|---|---|---|
| velocity | Verlet current/previous arrays | predictor/corrector | no dedicated pore-pressure velocity analogue |
| density | integrated with `Arc` inside stepper | predictor/corrector | PR rate from interaction, in-place Euler update |
| stress | trial plus constitutive correction inside stepper | predictor/corrector | not staged with stress |
| acceleration | computed in interaction and consumed by stepper | predictor and corrector interactions | feedback acceleration computed before scalar pressure update |
| pore pressure | no Verlet previous array | no predictor/corrector array | one explicit `p += rate dt` |

## External Acceleration and Coupling Placement

Hydromechanical feedback, hydromechanical damping, and mechanical top-load
acceleration are all applied to `Acec` inside `Interaction_Forces()`, before
the mechanical step uses `Acec`.

The current feedback acceleration is computed from the pressure field that
exists during interaction. The scalar pressure update then modifies
`PorePressc`, but this updated pressure does not affect `Acec` until the next
interaction stage.

This means mechanics sees pore pressure with one interaction-stage lag, while
the pressure equation sees divergence and Laplacian from the current
interaction stage. That is a legitimate first-order split, but it is not a
fully synchronized predictor-corrector coupling.

## Classification of Pore Pressure

Pore pressure currently behaves closest to an operator-split internal hydraulic
state:

- It is not density-like because it does not share density's predictor/corrector
  update.
- It is not stress-like because it is not updated inside
  `ComputeVerletVarsFluid()` / `ComputeSymplecticPre()` /
  `ComputeSymplecticCorr()`.
- It is acceleration-coupled because old pressure contributes to feedback
  acceleration, while the updated pressure is stored for the next interaction.

## Consistency Assessment

The implementation is internally consistent as an explicit operator split, but
it is not time-centered with the mechanical integrators.

The biggest mismatch is in Symplectic:

- the PR divergence term uses predicted/corrector mechanical variables;
- the diffusion term uses old pore pressure;
- the feedback acceleration uses old pore pressure;
- the updated pressure is written before the mechanical corrector but is not
  used by the same corrector acceleration.

This can create phase lag in feedback-on runs. It can also make boundary
operator changes appear more unstable because stronger boundary Laplacian
contributions enter the pressure update before the mechanical state has been
corrected.

