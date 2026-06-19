# dp002 full two-stage Cryer trial conclusion, 2026-06-19

This note records the `Dp=0.002` Cryer trial before deleting the heavy test
outputs from `refinement/dp002_full_20260619`.

## Configuration

- Particle spacing: `Dp=0.002`
- Particle generation: `setfrdrawmode auto="true"`
- Stage 1:
  - `HydroMechDrainage=0`
  - `HydraulicConductivity=0`
  - `HydroMechTopLoadMode=SphereNormal`
  - `HydroMechTopLoadQ0=10000 Pa`
  - `HydroMechTopLoadRampTime=0.005 s`
  - `SoilDampingCoef=0.02`
  - `TimeMax=0.082 s`
  - `DtFixed=1e-6`
- Stage 2 was corrected to use the restart time as the drainage origin:
  - `HydroMechDrainageStartTime=0`
  - `HydraulicConductivity=1e-4`
  - `TimeMax=0.0911 s`

## What ran

- Stage 1 completed normally.
- Stage 1 used `71170` fluid/free particles and `8045` loaded surface particles.
- Stage 1 load-area diagnostics were balanced in scalar area:
  - `A_sum=0.0314159`
  - `4*pi*R_eff^2=0.0314159`
  - `acc_range=[2324.42,2324.42]`
- Stage 1 completed `82001` steps with `0` excluded particles.
- Stage 1 runtime was `15454.244141 s`.
- The corrected Stage 2 was stopped intentionally after observing the Stage 1
  pore-pressure state. At the stop/check point it had reached `Part_0008`,
  about `t=0.020 s`, with no particle-out growth (`PartOut_000.obi4` stayed
  at `584 bytes`).

## Stage 1 pore-pressure conclusion

The undrained pressure accumulated under the external spherical load is still
not physically satisfactory at `Dp=0.002`.

From the final Stage 1 VTK frame `PartFluid_0041.vtk`:

- Center sample radius: `r <= 0.004 m`
- Center sample count: `58`
- Final center pressure: `p_center/q0 = 0.517825`
- Final core mean pressure (`r <= 0.01 m`): `p_core/q0 = 0.745932`
- Final free-surface mean pressure: `p_surface/q0 = 1.911549`
- Peak center pressure during Stage 1: `p_center/q0 = 0.518205` at `t=0.032 s`

Therefore, increasing resolution from `Dp=0.003` to `Dp=0.002` did not fix the
main Stage 1 problem. The pore-pressure field remains strongly nonuniform:
surface pressure is too high, center pressure remains far below the ideal
undrained target, and the interior/surface contrast persists even after the
long undrained loading stage.

## Decision

Do not continue this `Dp=0.002` full-cycle run for Cryer validation. Use
`Dp=0.003` as the working baseline resolution for the next tests, because it is
cheaper and the higher `Dp=0.002` resolution did not resolve the Stage 1
undrained-pressure defect.
