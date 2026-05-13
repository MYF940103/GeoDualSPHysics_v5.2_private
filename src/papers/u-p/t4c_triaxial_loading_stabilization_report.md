# T4c Triaxial Loading Stabilization Report

## Objective

T4c tests whether selected-confinement triaxial response can be stabilized by
staging confinement before axial compression and by using gentler axial loading.
The stage remains linear elastic: `SoilConstitutiveModel=0`, no DP baseline, no
MCC, no GPU run, and no Cryer boundary changes.

## Retained Cases

Directory:

`examples/u-pw/04_Undrained_Triaxial/experiments/T4c_LoadingStabilization/`

| Case | Gradient mode | Schedule |
| --- | ---: | --- |
| `CaseT4c_RawStagedLoading` | 0 | confinement ramp to 0.0010 s, axial start 0.0015 s, reaches -0.10 m/s2 |
| `CaseT4c_RenormStagedLoading` | 1 | same schedule |
| `CaseT4c_RawStagedGentleLoading` | 0 | confinement ramp to 0.0010 s, axial start 0.0015 s, reaches -0.04 m/s2 |

The retained gate ends at `0.0018 s`. An initial raw staged trial to `0.003 s`
lost particles after about `0.002 s`, so it was not retained as the T4c gate.

## Run Health

| Case | code | excluded | steps | DtMin adjusted | final `Kplastic` |
| --- | ---: | ---: | ---: | ---: | ---: |
| raw staged | 0 | 0 | 59 | 85 | 0 |
| renormalized staged | 0 | 0 | 72 | 109 | 0 |
| raw staged gentle | 0 | 0 | 59 | 85 | 0 |

All retained CPU Release smokes completed with no excluded particles and no
plasticity. PartVTK completed for all cases. GPU was not run.

## Confinement Diagnostics

| Metric | raw staged | renormalized staged |
| --- | ---: | ---: |
| active target count | 112 | 112 |
| cap axial leakage | 0 | 0 |
| lateral inward acceleration mean during ramp | 0.94 to 1.51 m/s2 | 1.89 to 3.02 m/s2 |
| net-force symmetry residual | order 1e-8 | order 1e-8 |

The selector remains effective: cap leakage stays zero. Renormalized gradient
again amplifies lateral confinement.

## Stability Result

| Case | final time [s] | final mean `PorePress` [Pa] | maxAbs `PorePressRate` [Pa/s] | final velocity max [m/s] | pressure reversal |
| --- | ---: | ---: | ---: | ---: | ---: |
| T4 raw reference | 0.001507 | -3.82e6 | approx 8.89e10 from mean | 38.16 | yes |
| T4b renormalized reference | 0.001505 | -1.46e7 | 2.01e12 | 87.68 | yes |
| raw staged | 0.001754 | -1.19e8 | 3.12e12 | 215.05 | yes |
| renormalized staged | 0.001752 | -1.89e8 | 3.08e12 | 212.17 | yes |
| raw staged gentle | 0.001754 | -1.19e8 | 3.12e12 | 215.05 | yes |

The pressure reversal appears around `t=0.0014 s`, before the T4c axial loading
starts at `t=0.0015 s`. This is the central T4c finding: staged axial loading
does not remove the instability because the confinement-only stage has already
become dynamically unstable.

## Answers Required by T4c

1. The T4b instability is most likely driven by the selected-confinement
   equilibration/u-pw feedback stage, not primarily by axial AccInput onset.
2. Staged loading did not eliminate `PorePressRate` excursions. It showed that
   the reversal begins before axial loading starts.
3. Gentler axial loading did not help in the retained short window because the
   main reversal occurs before the gentler loading becomes dynamically
   important.
4. Raw gradient is more stable than renormalized gradient in force magnitude.
   Renormalized confinement remains an amplifier.
5. `PorePressRate` excursions are not reduced enough for validation.
6. Pressure reversal is not fixed.
7. Cap leakage remains zero.
8. Lateral confinement remains geometrically coherent and symmetric, but the
   current dynamic response is too strong.
9. Source-level magnitude normalization or an explicit confinement-stage
   damping/equilibration mechanism is still needed. XML-only staging is not
   sufficient.
10. Do not enter T5 DP or T6 MCC. T4d output enhancement is useful, but the
    next physics task should continue stabilizing the confinement-only
    response first.

## Recommendation

Do not proceed to DP/MCC validation. The next task should be a small
source-level stabilization experiment for the selected flexible confinement
stage, preferably one of:

- `ConfiningStress` magnitude normalization/limiter for the active lateral
  target set;
- staged confinement equilibration support with stronger temporary damping;
- temporarily delaying or disabling pore-pressure Shepard during the
  confinement-only stage as a diagnostic, without changing the PR governing
  equation.
