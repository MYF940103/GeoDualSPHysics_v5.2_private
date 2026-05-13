# T4t True Platen Reaction Report

## Setup

T4t adds an opt-in CPU platen reaction diagnostic to the existing explicit
platen triaxial workflow. The cases are retained under:

```text
examples/u-pw/04_Undrained_Triaxial/experiments/T4t_TruePlatenReaction/
```

All cases use:

- top moving platen: `mkbound=1`, prescribed `v_z=-0.005 m/s`;
- bottom fixed platen: `mkbound=2`;
- specimen: `mkfluid=0`, `407` particles;
- selected lateral `FlexibleConfiningStress`;
- `PorePressureFeedback=0`;
- CPU Release only.

The new diagnostic is enabled with:

```xml
<parameter key="SavePlatenReactionDiagnostics" value="1" />
<parameter key="PlatenTopMkBound" value="1" />
<parameter key="PlatenBottomMkBound" value="2" />
<parameter key="PlatenReactionMode" value="0" />
<parameter key="PlatenReactionArea" value="0.0028274333882308137" />
```

## What Was Implemented

`PlatenReactionMode=0` accumulates the opposite of the specimen-side
fluid-bound SPH pair force contribution for pairs involving the selected top
or bottom platen `mkbound`. This is a true pairwise SPH interaction accumulator
for specimen-platen contact. It is not an acceleration-sum proxy and it is not
the old specimen-stress proxy.

It is also not a complete actuator reaction, because it does not include the
constraint force required to impose the prescribed platen motion.

## CPU Results

| Case | Result | Final `Kplastic` max | Final top/bottom reaction `Fz` | Final force balance error |
| --- | --- | ---: | ---: | ---: |
| elastic | `code=0`, `excluded=0`, `DtMin=0` | `0` | `1.04649 / -0.867504 N` | `0.093516` |
| DP high strength | `code=0`, `excluded=0`, `DtMin=0` | `0` | `1.04649 / -0.867504 N` | `0.093516` |
| DP mild yield | `code=0`, `excluded=0`, `DtMin=0` | `4.3803e-4` | `0.55936 / -0.426189 N` | `0.135124` |

The high-strength DP case remains effectively elastic and matches the elastic
baseline. The mild-yield case activates plasticity in the same stable
feedback-off platen workflow.

## Reaction Versus Previous Proxy

The previous proxy was:

```text
Fz_proxy = -mean(Sigma_zz)_specimen * pi * R^2
```

| Case | `Fz_proxy` | pairwise reaction average | Difference | Ratio |
| --- | ---: | ---: | ---: | ---: |
| elastic | `1.03854 N` | `0.956997 N` | `-0.08154 N` | `0.9215` |
| DP high strength | `1.03854 N` | `0.956997 N` | `-0.08154 N` | `0.9215` |
| DP mild yield | `0.48374 N` | `0.492775 N` | `0.00903 N` | `1.0187` |

The proxy is close enough for trend checks but no longer needs to be treated
as the only axial-force metric. Reaction-based axial stress is available for
T5b as a measurement diagnostic, with the caveat that it is a pairwise contact
reaction and not a full actuator constraint reaction.

## Platen and Measurement Checks

- Top prescribed displacement remains correct: final displacement is about
  `-3.00e-5 m`.
- Bottom platen remains fixed: displacement `0`.
- Specimen/platen/measurement grouping remains clean; center measurement
  contamination is `0`.
- Lateral confinement remains stable with `112` active lateral targets and
  zero cap leakage diagnostic.
- Full pore-pressure feedback remains disabled.

## Decision

T4t provides a usable CPU reaction diagnostic for the feedback-off explicit
platen route. The next reduced benchmark step can be T5b DP feedback-off
refinement using reaction-based axial stress. Full feedback, MCC, and GPU
triaxial validation should remain deferred.

