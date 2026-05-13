# T4k Initial Hydrostatic Confinement Report

## Objective

T4k tested whether a Zhao-style initial hydrostatic effective stress can stabilize the reduced triaxial specimen before feedback and axial loading. This stage did not enter DP, MCC, GPU execution, Cryer, or full triaxial reproduction.

## Implementation

`InitialStressMode=1` was added as a CPU-only opt-in mode. `InitialEffectiveStressIso` is interpreted as a positive compression magnitude, then written to the skeleton/effective stress tensor as negative diagonal `Sigmac`:

```text
InitialEffectiveStressIso = 50 Pa
Sigmac.xx = Sigmac.yy = Sigmac.zz = -50 Pa
```

The option does not initialize pore pressure, does not modify the PR pressure update, does not change `SoilConstitutiveModel`, and does not alter `FlexibleConfiningStress`. Default behavior remains unchanged because `InitialStressMode=0`.

Build checks:

- CPU Release: passed.
- CPU Debug: passed with existing third-party PDB warnings.
- GPU Release: passed; GPU execution was not run. Non-default initial stress is CPU-only and hard-errors on GPU.

## CPU Cases

All cases used the reduced T4 triaxial cylinder, `SoilConstitutiveModel=0`, `HydraulicElevationSource=0`, `PorePressureBoundaryOperator=0`, selected lateral flexible confinement where enabled, and no axial loading unless explicitly optional.

| Case | Result | Notes |
|---|---|---|
| Initial stress only, feedback off | `code=0`, `excluded=0`, `Kplastic=0`, `DtMin=0` | Stable numerically, but free-surface unbalanced initial stress produced immediate negative pore pressure. |
| Initial stress + selected flexible confinement, feedback off | `code=0`, `excluded=0`, `Kplastic=0`, `DtMin=0` | Lateral selector remained coherent and cap leakage stayed zero, but the state was still not hydrostatically balanced. |
| Initial stress + selected flexible confinement, delayed feedback | `code=0`, `excluded=0`, `Kplastic=0`, `DtMin=0` | Full delayed feedback still caused a large dynamic excursion. |
| Axial smoke | Not run | The confinement-only feedback gate did not pass. |

## Key Metrics

| Case | Max `PorePressRate` | Max velocity | Final center `PorePress` | Final negative count | Final `q` proxy |
|---|---:|---:|---:|---:|---:|
| Initial stress only, feedback off | `4.63e7 Pa/s` | `1.18e-3 m/s` | `-2.07e4 Pa` | `407/407` | `11.30 Pa` |
| Initial stress + confinement, feedback off | `4.48e7 Pa/s` | `1.31e-3 m/s` | `-1.10e4 Pa` | `407/407` | `51.47 Pa` |
| Initial stress + confinement, delayed feedback | `1.59e12 Pa/s` | `37.51 m/s` | `-1.99e7 Pa` | `407/407` | `4.66e4 Pa` |

Confinement diagnostics stayed geometrically clean in the selected cases:

- active targets: `112`;
- cap axial leakage: `0`;
- lateral inward acceleration: coherent, about `1.5-1.9 m/s2` near full ramp;
- net force symmetry residual: small.

## Interpretation

Initial hydrostatic effective stress was implemented correctly and initialized the stress field with `q=0` at frame 0. However, the reduced cylinder still lacks matching external hydrostatic boundary support on the caps and free surfaces. A uniform effective stress state in a free-surface SPH cloud is therefore not a quiet equilibrium state by itself.

Adding selected lateral flexible confinement partially reduced the center pore-pressure drift in feedback-off mode, but it did not produce a full 3D hydrostatic balance. When full delayed pore-pressure feedback was re-enabled, the case again developed a T4e/T4f-scale feedback runaway.

## Answers

1. Initial hydrostatic effective stress was implemented.
2. The stress convention is: positive XML compression magnitude becomes negative `Sigmac` diagonal stress.
3. Default behavior is unchanged.
4. Initial stress only is numerically stable (`code=0`, no excluded/DtMin), but not physically equilibrated because the free surface emits a pore-pressure/stress response.
5. Initial stress + selected flexible confinement is also numerically stable with feedback off, but still not hydrostatically balanced.
6. Delayed full feedback still triggers a large excursion; it does not pass the confinement-only gate.
7. `PorePressRate` improves only for feedback-off cases. Full feedback remains at `~1e12 Pa/s`.
8. Axial loading was not reintroduced.
9. Feedback limiter/cap is still not a physical solution.
10. The next step should not be DP/MCC. The remaining blocker is a true staged hydrostatic confinement equilibrium: cap/axial confinement or restart-based equilibration before full feedback.
11. GPU remains deferred.

## Recommendation

Proceed to a T4l design focused on full hydrostatic confinement staging, not DP/MCC:

- add or emulate axial/cap confinement so the initial effective stress is balanced in all principal directions;
- consider a restart/stage workflow after feedback-off equilibration;
- only then test full feedback and gentle axial loading.

DP and MCC should remain deferred until a stable elastic selected-confinement baseline exists.
