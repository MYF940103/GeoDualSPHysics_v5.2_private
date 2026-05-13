# M3c MCC CPU Stress Update Plan

## Objective

M3c should connect the verified M3a C++ MCC helper to the CPU SPH stress update as `SoilConstitutiveModel=3`.

M3c should remain CPU-only, feedback-off, and explicit-platen focused. GPU and full pore-pressure feedback stay deferred.

## Files Likely Touched

- `source/JSph.cpp`: parser refinement if additional MCC controls are needed.
- `source/DualSphDef.h`: parameter/state declarations if M3b fields need adjustment.
- `source/JSphCpu.cpp`: `ApplySoilConstitutiveModelCpu` model `3` branch.
- `source/JSphCpuSingle.cpp`: initialization/output updates if stress-update diagnostics are expanded.
- MCC helper files under `papers/u-p/mcc_single_point/cpp/`, or a production-safe copy under `source/` if needed.

## Stress Convention Boundary

Current SPH stress:

```text
Sigmac compression is negative.
```

MCC helper convention:

```text
compression-positive effective stress.
p' = -trace(Sigmac)/3
```

M3c should convert at the constitutive boundary only:

1. receive elastic trial `sigma_e` in current `Sigmac` convention;
2. map to MCC compression-positive stress;
3. call local MCC update;
4. map updated stress back to negative-compression `Sigmac`;
5. update MCC state arrays.

## State Update

For each material particle:

- read `MccPc`;
- read `MccVoidRatio`;
- read `MccPlasticVolStrain`;
- read `MccEqPlasticStrain`;
- call helper return mapping;
- write updated stress;
- write updated MCC state;
- write `MccYieldFlag`;
- write `MccPlasticMultiplier`;
- write `MccReturnStatus`;
- write `MccReturnIterations`;
- write `MccYieldResidual`.

`Kplastic` may be set to an MCC equivalent plastic strain diagnostic for compatibility, but it should not replace MCC-specific state.

## Failure Handling

M3c must hard-error, not silently fallback, when:

- `p' <= MccTensionCutoff` and no valid tension handling is defined;
- Newton fails to converge;
- `pc <= 0`;
- state arrays are missing;
- model `3` is requested on GPU.

Temporary elastic fallback is not acceptable for M3c stress-update validation.

## First CPU SPH Smokes

Use the T5 feedback-off explicit-platen workflow:

1. high-`pc` elastic-like MCC smoke;
2. mild-yield MCC smoke.

Both should use:

- `PorePressureFeedback=0`;
- explicit top/bottom platens;
- selected lateral `FlexibleConfiningStress`;
- `SaveMccState=1`;
- pairwise platen reaction diagnostics if available;
- CPU Release only.

No DP/MCC paper reproduction should be attempted in M3c.

## Output Requirements

M3c should retain M3b output fields and additionally verify that:

- `MccYieldFlag` changes when yielding occurs;
- `MccPlasticVolStrain` and `MccEqPlasticStrain` evolve smoothly;
- `MccYieldResidual` remains small after plastic returns;
- `MccReturnStatus` stays converged.

## Restart Requirements

Before long or staged MCC runs, restart must save and reload all MCC fields:

- `MccPc`;
- `MccVoidRatio`;
- `MccPlasticVolStrain`;
- `MccEqPlasticStrain`;
- `MccYieldFlag`;
- `MccPlasticMultiplier`;
- `MccReturnStatus`;
- `MccReturnIterations`;
- `MccYieldResidual`.

If restart is incomplete, stop at short non-restart smoke tests.

## No-Go Criteria

Stop M3c if:

- CPU build fails;
- model `3` accepts missing/invalid MCC parameters;
- GPU accepts model `3`;
- local return mapping silently fails;
- `excluded > 0`, DtMin burst, velocity blow-up, nonpositive `pc`, or uncontrolled `p' <= 0` appears in first smokes;
- full feedback is needed to make a smoke pass.

## Deferred

Deferred beyond M3c:

- full pore-pressure feedback;
- GPU MCC implementation;
- strict paper triaxial reproduction;
- long MCC response;
- calibrated MCC parameter studies.
