# Zhao-style Flexible Confinement Validation Notes

Date: 2026-06-19

## Test folder

- Branch test files: `refinement/zhao_flexconf`
- Solver output: `refinement/zhao_flexconf/out/stage1`
- Particle VTK: `refinement/zhao_flexconf/out/stage1/particles`
- Analysis output: `refinement/zhao_flexconf/analysis`

## Setup

- Particle generation: `setfrdrawmode auto="true"`
- `dp = 0.003 m`
- `HydroMechTopLoadMode = FlexibleConfinement`
- `HydroMechTopLoadQ0 = 10000 Pa`
- `HydroMechTopLoadRampTime = 0.005 s`
- `HydroMechDrainage = 0`
- `HydraulicConductivity = 0`
- `SoilDampingCoef = 0.02`
- `TimeMax = 0.006 s`
- `TimeOut = 0.001 s`

## Result

The first implementation attempt used the wrong sign for the kernel-truncation
stress term. `HydroMechLoadAce` pointed outward and the pore pressure became
approximately `-q0`. After reversing the sign, the acceleration field is
compressive and the Stage1 pore pressure follows the load ramp.

Sign-corrected uncorrected confinement result at `t = 0.006 s`:

- nearest-center pore pressure: `9905.52 Pa` (`0.9906 q0`)
- core mean pore pressure, `r <= 0.006 m`: `9895.00 Pa` (`0.9895 q0`)
- free-surface mean pore pressure: `9968.28 Pa` (`0.9968 q0`)
- center speed: `1.60e-4 m/s`
- free-surface particles: `3630`
- particles with nonzero `HydroMechLoadAce`: `22483`

The corresponding previous FrDraw + area-normalized `SphereNormal` short test
at the same `dp`, `TimeMax`, and low damping had:

- nearest-center pore pressure: about `3144 Pa`
- core mean pore pressure: about `4741 Pa`
- surface mean pore pressure: about `16636 Pa`

## Interpretation

The minimal Zhao-style uncorrected kernel-truncation confinement strongly
improves the undrained Stage1 initial pressure state. It removes the severe
center pressure deficit and the surface overpressure seen when load is applied
only to the detected free surface.

However, because this validation branch intentionally uses the uncorrected
kernel gradient, the diagnostic load term is not strictly localized to the
free surface: all fluid particles have a nonzero residual `HydroMechLoadAce`.
The interior load is much smaller than the surface load but not zero. This is
the main limitation of the current minimal branch and the next improvement
should test gradient/kernel normalization or the correction terms described by
Zhao et al. before considering this production-ready.

## Gradient-Corrected Test

Same setup, but with `HydroMechTopLoadMode = FlexibleConfinementCorrected`,
uses the existing SPH correction matrix to correct the confinement kernel
gradient before adding `HydroMechLoadAce`.

Result at `t = 0.006 s`:

- nearest-center pore pressure: `11040.51 Pa` (`1.1041 q0`)
- core mean pore pressure, `r <= 0.006 m`: `13166.21 Pa` (`1.3166 q0`)
- free-surface mean pore pressure: `21586.96 Pa` (`2.1587 q0`)
- free-surface pore pressure range: `19260.72 Pa` to `21698.93 Pa`
- mean `HydroMechLoadAce` magnitude: `506.83 m/s^2`
- mean radial load component: `-498.79 m/s^2`

For comparison, the uncorrected confinement branch at the same time had:

- nearest-center pore pressure: `9905.52 Pa`
- core mean pore pressure, `r <= 0.006 m`: `9895.00 Pa`
- free-surface mean pore pressure: `9968.28 Pa`
- mean `HydroMechLoadAce` magnitude: `298.18 m/s^2`
- mean radial load component: `-289.50 m/s^2`

Conclusion: the direct gradient-corrected confinement term worsens this Cryer
Stage1 test. It amplifies the effective confinement load and produces strong
surface overpressure instead of improving the nearly uniform undrained pressure
state. The current best validation branch remains
`HydroMechTopLoadMode = FlexibleConfinement` without gradient correction.
The corrected-gradient mode was removed from the code interface after this
comparison; use numeric `HydroMechTopLoadMode=3` for the remaining
`FlexibleConfinement` branch.

The next correction attempt should not simply apply the corrected gradient to
all particles. A better follow-up is to use Zhao et al.'s near-boundary support
criterion or an equivalent `PosDiv`/free-surface-based limiter, and then
renormalize the total applied confinement so the effective pressure remains
`q0`.
