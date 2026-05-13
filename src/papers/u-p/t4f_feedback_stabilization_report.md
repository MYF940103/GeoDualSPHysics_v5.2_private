# T4f Feedback Stabilization Report

## Setup

T4f keeps the T4e selected-confinement reduced cylinder:

- `SoilConstitutiveModel=0`;
- `PorePressureBoundaryOperator=0`;
- `HydraulicElevationSource=0`;
- selected `FlexibleConfiningStress` with `f_i` and lateral selector enabled;
- no Cryer boundary modes;
- CPU Release only, no GPU simulation.

The feedback gate uses delayed restoration:

```xml
PorePressureFeedbackStartTime = 0.003
PorePressureFeedbackRampEndTime = 0.0045
PorePressureFeedbackScale = 1
```

## Source Change

T4f adds opt-in feedback acceleration diagnostics and stabilization:

- `SavePorePressureFeedbackDiagnostics`;
- `PorePressureFeedbackDiagInterval`;
- `PorePressureFeedbackRelaxation`;
- `PorePressureFeedbackLimiterMode`;
- `PorePressureFeedbackMaxAccel`;
- `PorePressureFeedbackMaxAccelRatio`.

Defaults preserve the old behavior. The PR pressure-rate equation and the soil
constitutive model are unchanged.

## Case Results

| Case | Code/excluded | DtMin | Max PorePressRate | Max velocity | Center reversal | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| feedback off reference | `0 / 0` | `0` | `2.11e7 Pa/s` | `7.57e-4 m/s` | no | Stable reference. |
| full feedback, no stabilization | `0 / 164` | `256` | `1.30e13 Pa/s` | `572 m/s` | yes | Reproduces T4e failure. |
| relaxation `alpha=0.2` | `0 / 0` | `99` | `3.17e12 Pa/s` | `220 m/s` | yes | Relaxation alone is insufficient. |
| cap `50 m/s2`, ratio `25` | `0 / 0` | `0` | `9.75e8 Pa/s` | `4.58e-2 m/s` | yes | Removes DtMin/exclusion but not center reversal. |
| relaxation `0.2` + cap `50 m/s2`, ratio `25` | `0 / 0` | `0` | `1.03e9 Pa/s` | `5.84e-2 m/s` | no | Best confinement-only full-feedback case. |
| relaxation `0.2` + cap `10 m/s2`, ratio `5` | `0 / 0` | `0` | `2.77e8 Pa/s` | `1.41e-2 m/s` | yes, at final frame | Lower cap suppresses rate/velocity but over-damps into weak reversal. |
| gentle axial after best confinement gate | `0 / 0` | `0` | `1.07e9 Pa/s` | `6.12e-2 m/s` | yes, after axial onset | Axial loading still reintroduces reversal. |

`Kplastic=0` in every T4f case.

## Feedback Operator Findings

The direct feedback acceleration is the amplifier. With full feedback and no
stabilization, raw/used feedback acceleration reaches `1.58e7 m/s2` and the
run develops exclusions and `256` DtMin adjustments. Relaxation alone reduces
the instantaneous jump only partially; the operator still grows to order
`1e6 m/s2` used acceleration and destabilizes.

The cap cases show that limiting the acceleration itself is effective at
removing the DtMin burst and velocity blow-up. The best diagnostic case keeps
full feedback scale `1`, caps used feedback acceleration at `50 m/s2`, and
uses relaxation `alpha=0.2`.

## Remaining Issues

The best confinement-only case is numerically much better but not validation
ready:

- max `PorePressRate` is reduced by roughly four orders of magnitude from
  `1e13` to `1e9 Pa/s`, but it is still far above the feedback-off reference;
- local negative pressures remain near the outer/edge region;
- stronger cap `10 m/s2` reduces rate further but causes a final center-core
  reversal, suggesting the limiter changes the coupled equilibration path;
- gentle axial loading after the best confinement gate still triggers
  center-core reversal after axial onset.

## Answers

1. The feedback acceleration is a direct dynamic amplifier of the selected
   confinement instability.
2. T4f implements opt-in relaxation and absolute/ratio caps; old default
   behavior is unchanged.
3. Relaxation alone is not effective.
4. Acceleration caps are effective at removing excluded particles and DtMin
   bursts.
5. Full feedback scale `1` can be made confinement-only stable in the limited
   sense of `code=0`, `excluded=0`, `DtMin=0`, and no center-core reversal for
   the best cap case.
6. The pressure-rate artifact is reduced strongly but not to the feedback-off
   level.
7. Axial loading is not yet safe: the short axial smoke reintroduces reversal.
8. DP and MCC remain deferred.

## Recommendation

Do not enter T5 DP or T6 MCC. The next step should be a focused T4g feedback
formulation audit rather than more loading variants: determine whether the
feedback acceleration should be computed from total pressure, excess pressure,
filtered pressure, a corrected/renormalized gradient, or a more conservative
effective-stress coupling form. The limiter is useful as a diagnostic safety
guard, but it is not yet a validation-quality physical fix.
