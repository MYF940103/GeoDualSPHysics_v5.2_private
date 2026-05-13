# T4c Triaxial Loading Stability Audit

## Scope

T4c audits the T4/T4b selected-confinement instability before any DP or MCC
triaxial baseline. The objective is to determine whether the late pressure
reversal and large `PorePressRate` excursions are driven primarily by axial
AccInput loading, confinement ramping, renormalized confinement magnitude, or
the current reduced u-pw triaxial workflow itself.

## Inputs Reviewed

- T4 selected-confinement raw-gradient metrics.
- T4b renormalized-gradient metrics.
- T4c staged-loading short smokes:
  - `CaseT4c_RawStagedLoading`
  - `CaseT4c_RenormStagedLoading`
  - `CaseT4c_RawStagedGentleLoading`

The T4c XML variants use `SoilConstitutiveModel=0`, `PorePressureBoundaryOperator=0`,
`HydraulicElevationSource=0`, selected flexible confinement, and CPU Release
only. They do not touch Cryer boundary modes.

## T4/T4b Instability Timing

T4 raw selected confinement showed a clear reversal between `t=0.001305 s`
and `t=0.001400 s`:

| time [s] | mean `PorePress` [Pa] | mean `PorePressRate` [Pa/s] | max velocity [m/s] |
| ---: | ---: | ---: | ---: |
| 0.001305 | 6.62e4 | 3.38e8 | 2.71 |
| 0.001400 | -9.70e4 | -1.38e9 | 11.01 |
| 0.001507 | -3.82e6 | -8.89e10 | 38.16 |

T4b renormalized confinement made the same pattern stronger:

| time [s] | mean `PorePress` [Pa] | maxAbs `PorePressRate` [Pa/s] | max velocity [m/s] |
| ---: | ---: | ---: | ---: |
| 0.001304 | 1.20e5 | 7.99e10 | 5.28 |
| 0.001394 | -3.95e5 | 3.10e11 | 20.93 |
| 0.001505 | -1.46e7 | 2.01e12 | 87.68 |

The renormalized correction roughly doubled lateral inward acceleration and
therefore amplified the instability.

## T4c Findings

T4c delays axial loading until `t=0.0015 s` and extends the confinement ramp to
`t=0.0010 s`. Despite this, the pressure reversal still appears around
`t=0.0014 s`, before axial AccInput starts. This is the most important result
of T4c.

| Case | final time [s] | excluded | DtMin adjustments | final mean `PorePress` [Pa] | maxAbs `PorePressRate` [Pa/s] | pressure reversal |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| raw staged | 0.001754 | 0 | 85 | -1.19e8 | 3.12e12 | yes |
| renormalized staged | 0.001752 | 0 | 109 | -1.89e8 | 3.08e12 | yes |
| raw staged gentle | 0.001754 | 0 | 85 | -1.19e8 | 3.12e12 | yes |

The first attempted longer raw-staged run to `0.003 s` lost particles after
about `0.002 s`; the retained T4c gate is therefore a short stability window
ending at `0.0018 s`.

## Region and Event Diagnosis

- The excursion is not limited to the measurement region. Full-specimen and
  center-region mean pressures reverse together.
- The reversal occurs before the delayed axial AccInput onset, so axial loading
  is not the first trigger.
- The excursion follows the confinement ramp and coincides with the step-10
  pore-pressure Shepard regularization event around `t=0.001306 s`.
- `DivVel` changes sign at the same time as `PorePressRate`, indicating a
  hydromechanical wave or volume-change artifact rather than a simple pressure
  postprocessing issue.
- Velocity max grows rapidly after the reversal. In the retained T4c window it
  reaches about `215 m/s` for raw staged and about `212 m/s` for renormalized
  staged.
- Cap leakage remains zero in all selected-confinement variants.
- Lateral confinement remains symmetric and coherent, but the current workflow
  is still dynamically too violent for validation.

## Source of Instability

The most likely source is not the axial loading onset. The evidence points to
the selected-confinement-only stage interacting with the current u-pw pressure
feedback, hydromechanical damping, and Shepard smoothing. Renormalized
confinement is a magnitude amplifier, not a cure.

The T4c result therefore redirects the next step toward stabilizing the
confinement equilibration stage itself, before any DP or MCC stress-path work.
