# M3c MCC CPU Stress Update Report

## Objective

M3c connects `SoilConstitutiveModel=3` to a CPU Modified Cam Clay stress update
branch. It is still a short, feedback-off SPH smoke stage, not a full MCC paper
validation.

## Implementation

`SoilConstitutiveModel=3` now calls a CPU MCC return-mapping helper in
`JSphCpu.cpp`. The helper follows the M2/M3a formulation:

```text
f = q^2 + M^2 p'(p' - pc)
unknowns = p, q, pc, Delta_gamma
compression-positive MCC internals
Sigmac mapping: stress_cp = -Sigmac, p' = -trace(Sigmac)/3
```

The code copies the M3a parity-tested logic into the production CPU source
rather than linking the standalone research helper into the solver build.
Models `0/1/2` keep their existing branches.

MCC updates:

- `Sigmac`
- `MccPc`
- `MccVoidRatio`
- `MccPlasticVolStrain`
- `MccEqPlasticStrain`
- `MccYieldFlag`
- `MccPlasticMultiplier`
- `MccReturnStatus`
- `MccReturnIterations`
- `MccYieldResidual`

`Kplastic` is mapped to `MccEqPlasticStrain` as a compatibility diagnostic.

## Smoke Cases

Cases are retained in:

`examples/u-pw/04_Undrained_Triaxial/experiments/M3c_MCCStressUpdateCpu/`

Both cases use the explicit platen workflow, selected lateral
FlexibleConfiningStress, `InitialEffectiveStressIso=50 Pa`,
`PorePressureFeedback=0`, `SaveMccState=1`, and pairwise platen reaction
diagnostics.

| Case | pc0 | Result |
| --- | ---: | --- |
| `CaseM3c_MCCHighPc_ElasticLike` | `100000 Pa` | `code=0`, `excluded=0`, `DtMin=0` |
| `CaseM3c_MCCMildYield` | `120 Pa` | `code=0`, `excluded=0`, `DtMin=0` |

## Key Metrics

Final saved-frame metrics:

| Metric | High-pc MCC | Mild MCC |
| --- | ---: | ---: |
| axial strain proxy | `2.05e-4` | `1.42e-4` |
| p' proxy | `146.59 Pa` | `47.64 Pa` |
| q proxy | `355.55 Pa` | `62.68 Pa` |
| Fz proxy | `1.0847 N` | `0.2528 N` |
| mean pore pressure | `2.62e4 Pa` | `-5.51e4 Pa` |
| Kplastic max | `0` | `7.07e-4` |
| MccPc mean | `100000 Pa` | `119.93 Pa` |
| MccVoidRatio mean | `0.79989` | `0.80009` |
| MccYieldFlag fraction | `0` | `1.0` |
| max return iterations | `0` | `24` |
| max raw yield residual | elastic margin, not Newton residual | `1.13e-4` |

High-pc MCC is elastic-like: no MCC yield flags, no plastic strain, and the
stress path remains close to the T5b elastic/high-strength DP reference.

Mild MCC yields across the specimen. `pc`, void ratio, plastic volumetric
strain, equivalent plastic strain, plastic multiplier, return iterations, and
yield residual all update and output correctly.

## Stability

Both CPU Release smokes satisfy:

- `code=0`
- `excluded=0`
- `DtMin=0`
- no NaN/Inf observed in saved diagnostics
- top platen prescribed motion remains active
- bottom platen remains fixed
- lateral target count remains `112`
- cap leakage diagnostic remains `0`

Pore pressure remains bounded in the short feedback-off runs. Mild MCC has
negative mean pore pressure, which is consistent with the reduced feedback-off
diagnostic status and is not strict undrained validation.

## Builds

Completed:

- CPU Release build: passed
- CPU Debug build: passed, with existing third-party debug PDB warnings
- GPU Release build: passed

No GPU simulation was run. `SoilConstitutiveModel=3` remains GPU-hard-error.

## Remaining Limits

M3c is not strict MCC validation because:

- full pore-pressure feedback remains disabled;
- the elastic predictor is still the existing linear `E,nu` stress-rate path;
- no kappa-based nonlinear elasticity has been added;
- restart persistence of MCC state is not extended beyond the current output
  skeleton;
- pairwise platen reaction is not a full actuator reaction;
- no GPU MCC path exists.

## Next Step

M3d can refine the feedback-off MCC platen workflow:

1. compare high-pc MCC more formally against T5b elastic/high-strength DP;
2. tune one mild-yield MCC smoke, without broad parameter sensitivity;
3. inspect return-status maps and residual normalization;
4. decide whether nonlinear MCC elasticity is needed before longer SPH runs.

Full feedback and GPU remain deferred.
