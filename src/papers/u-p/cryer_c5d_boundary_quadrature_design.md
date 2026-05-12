# C5d Boundary Quadrature Design

Date: 2026-05-12

## Objective

C5c showed that the curved drained boundary ghost state can be exactly
prescribed while the material particles in the near-surface shell still retain
a systematic positive excess pore pressure. The purpose of C5d is therefore to
add a more principled operator-level Dirichlet boundary coupling for
`PorePressureBoundaryOperator=3` without using the diagnostic material clamp.

This design remains CPU-only and experimental. It does not change the PR
governing equation, the flexible confining stress term, the constitutive model,
or the legacy boundary modes.

## Mode Definition

`CurvedDrainedBoundaryMode` is extended as follows:

| Mode | Meaning | Production status |
|---|---|---|
| `0` | First-order spherical Dirichlet ghost | Experimental baseline |
| `1` | Strengthened image Dirichlet ghost | Experimental |
| `2` | Diagnostic material surface clamp | Diagnostic only, not production |
| `3` | Multi-sample spherical Dirichlet boundary quadrature | CPU-only experimental |

Mode `3` is intended as a production-candidate experiment. It is not a material
pressure clamp: material particle pressure is never overwritten.

## Sample Placement

For each material particle inside the curved drained near-surface shell:

1. Compute the radial direction
   `n = (x_i - c) / |x_i - c|`.
2. Project that direction to the spherical drained surface
   `x_s = c + R n`.
3. Build a local tangent basis `t1`, `t2`.
4. Construct five spherical boundary samples:
   one projected sample and four tangent-shifted samples.
5. Re-project each shifted location to the spherical surface and place it on a
   thin exterior shell at `R + normal_offset`.

The exterior shell offset avoids a zero-distance pair when the material
particle lies very close to the prescribed boundary.

## Boundary State

For strict Cryer with `HydraulicElevationSource=0`, the drained value is simply

```text
p_b = 0
excess_b = 0
```

For the general existing convention, mode `3` follows the current curved
drained settings:

- if `CurvedDrainedBoundaryUseExcess=1`, the prescribed value is interpreted as
  an excess pore pressure;
- otherwise it is interpreted as total pore pressure.

The sample contribution enters `LapPorePress` and `LapZ` before
`PorePressRate` is assembled. With `HydraulicElevationSource=0`, the `LapZ`
field can still be diagnosed, but it is not used in the pressure rate.

## Quadrature Weight

The first implementation uses the material particle volume as the local
measure and splits an effective quadrature volume over the five samples:

```text
V_sample = V_i * max(1, h/dp) / 5
```

This is deliberately conservative. It strengthens the operator-level
Dirichlet coupling relative to a single ghost point while avoiding the
instantaneous removal produced by the diagnostic surface clamp.

This weighting is not a final MLS or surface-area quadrature rule. It is a
minimal, local test of whether multiple spherical Dirichlet samples materially
improve the Cryer surface-layer residual.

## Why This Is Not A Clamp

Mode `3` does not set `PorePress_i` or `ExcessPorePress_i` on material
particles. It only adds boundary-sample terms to the same SPH hydraulic
operator used for `LapPorePress` and `LapZ`. The material field evolves through
the normal PR pressure-rate update.

Mode `2` remains the diagnostic clamp and is retained only as an upper-bound
comparison for the question: "What would happen if the material surface layer
were forcibly drained?"

## Stability Controls

The mode is kept CPU-only and off by default. Diagnostics record:

- number of material particles receiving boundary quadrature;
- number of virtual boundary samples;
- average sample count per material particle;
- estimated boundary contribution magnitude;
- near-surface excess residual;
- pressure-rate magnitude and velocity response.

If mode `3` produces only marginal improvement, the correct conclusion is not
that the drained boundary is solved. It means a fuller MLS/boundary quadrature
or geometry/resolution refinement is still needed before C6 quantitative
comparison.
