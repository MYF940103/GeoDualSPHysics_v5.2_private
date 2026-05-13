# T5b DP Feedback-Off Platen Refinement Report

## Setup

T5b is retained under:

```text
examples/u-pw/04_Undrained_Triaxial/experiments/T5b_DPFeedbackOffRefinement/
```

All cases use the explicit platen workflow:

- top platen: moving `mkbound=1`, prescribed `v_z=-0.005 m/s`;
- bottom platen: fixed `mkbound=2`;
- specimen: `mkfluid=0`, `407` particles;
- selected lateral `FlexibleConfiningStress`;
- `SavePlatenReactionDiagnostics=1`;
- `PorePressureFeedback=0`;
- CPU Release only.

Cases:

| Case | Constitutive setup | Purpose |
| --- | --- | --- |
| `CaseT5b_Elastic_ReactionRefinement` | `SoilConstitutiveModel=0` | elastic reference |
| `CaseT5b_DPHighStrength_ReactionRefinement` | DP, `phi=33 deg`, `coh=10000 Pa`, `dlt=0` | elastic-like DP reference |
| `CaseT5b_DPMildYield_ReactionRefinement` | DP, `phi=30 deg`, `coh=50 Pa`, `dlt=0` | plastic activation diagnostic |

No optional longer mild-yield case was added; the three required lines were
sufficient for this reduced refinement.

## Run Health

| Case | Result | `DtMin` | Final `Kplastic` max | Plastic count |
| --- | --- | ---: | ---: | ---: |
| elastic | `code=0`, `excluded=0` | `0` | `0` | `0` |
| DP high strength | `code=0`, `excluded=0` | `0` | `0` | `0` |
| DP mild yield | `code=0`, `excluded=0` | `0` | `4.3803e-4` | `341/407` |

The top platen reaches the expected final displacement of about `-3.00e-5 m`;
the bottom platen remains fixed. No NaN/Inf behavior was detected in the
postprocessed metrics.

## Lateral Confinement

The lateral confinement diagnostic is unchanged and stable:

- active targets: `112`;
- lateral `f_i` selected: `112`;
- cap axial leakage diagnostic: `0`;
- final lateral inward acceleration mean: `1.87224 m/s2`.

## Pairwise Reaction and Proxy Comparison

`PlatenReactionMode=0` reports pairwise specimen-platen interaction reaction,
not actuator/constraint reaction. The old proxy remains:

```text
Fz_proxy = -mean(Sigma_zz)_specimen * pi * R^2
```

Final comparison:

| Case | Top/bottom `Fz` | Pairwise avg | `Fz_proxy` | Pairwise/proxy |
| --- | ---: | ---: | ---: | ---: |
| elastic | `1.04649 / -0.867504 N` | `0.956997 N` | `1.03854 N` | `0.9215` |
| DP high strength | `1.04649 / -0.867504 N` | `0.956997 N` | `1.03854 N` | `0.9215` |
| DP mild yield | `0.55936 / -0.426189 N` | `0.492775 N` | `0.48374 N` | `1.0187` |

The pairwise reaction is therefore usable for reduced axial stress-strain
curves. It should still be described with the T4t caveat: it does not include
the full prescribed-motion actuator reaction.

## Stress Path and Pore Pressure

Final specimen-wide proxies:

| Case | `p'` proxy | `q` proxy | Mean pore pressure | MaxAbs `PorePressRate` |
| --- | ---: | ---: | ---: | ---: |
| elastic | `145.66 Pa` | `332.47 Pa` | `4.54e4 Pa` | `2.04e7 Pa/s` |
| DP high strength | `145.66 Pa` | `332.47 Pa` | `4.54e4 Pa` | `2.04e7 Pa/s` |
| DP mild yield | `86.58 Pa` | `126.76 Pa` | `1.49e4 Pa` | `1.03e7 Pa/s` |

The elastic and high-strength DP curves are identical over this short window,
as expected. The mild-yield DP case reduces `q`, reaction force, pore pressure,
and velocity while activating `Kplastic`.

The `p'-q` path remains a specimen-stress proxy, not a strict paper stress
path. It is more readable than the earlier AccInput route because platen
particles are excluded and the reaction diagnostic is available.

## Decision

T5b passes as a reduced DP feedback-off platen refinement. It supports moving
to T5c for a slightly longer DP feedback-off response, still with the same
reduced caveats.

Do not start MCC or full feedback from this result. A future T4u-style true
actuator reaction patch may still be useful before paper-level axial stress
validation, but it is not required before T5c reduced DP trend work.

GPU remains deferred.

