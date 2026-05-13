# M3b MCC SPH Integration Preplan

## Objective

M3b should begin integrating the verified C++ MCC helper into the CPU solver, but only as an opt-in `SoilConstitutiveModel=3` path. It should not enable full feedback or GPU.

## Parser

Extend `SoilConstitutiveModel`:

```text
0 = linear elastic skeleton
1 = Drucker-Prager
2 = Drucker-Prager softening
3 = Modified Cam Clay
```

Required MCC parameters:

- `MccLambda`;
- `MccKappa`;
- `MccM`;
- `MccInitialVoidRatio` or `MccInitialSpecificVolume`;
- `MccInitialPreconsolidationPressure` or `MccOCR`;
- `MccTensionCutoff`;
- `MccReturnTolerance`;
- `MccReturnMaxIter`;
- `SaveMccState`.

GPU should hard-error if model `3` is requested.

## State Arrays

Add CPU arrays for:

- `MccPc`;
- `MccVoidRatio` or `MccSpecificVolume`;
- `MccPlasticVolStrain`;
- `MccEqPlasticStrain`;
- `MccYieldFlag`;
- `MccPlasticMultiplier`;
- optional `MccReturnIterations` and `MccReturnStatus`.

Do not replace these with `Kplastic`. `Kplastic` can remain a compatibility equivalent plastic measure.

## Initialization

At initialization:

1. initialize `Sigmac` as today;
2. compute `p' = -trace(Sigmac)/3`;
3. initialize `p_c` directly or through OCR;
4. initialize void ratio/specific volume;
5. zero MCC plastic diagnostics;
6. error if `p' <= MccTensionCutoff`.

## Output

When `SaveMccState=1`, output:

- `MccPc`;
- `MccVoidRatio` or `MccSpecificVolume`;
- `MccPlasticVolStrain`;
- `MccEqPlasticStrain`;
- `MccYieldFlag`;
- `MccPlasticMultiplier`;
- optional `MccReturnIterations`.

Existing stress output should remain unchanged.

## Restart

MCC restart must restore:

- `Sigma_kk`;
- `Sigma_ij`;
- `Kplastic`;
- `PorePress` when active;
- all MCC state arrays.

If model `3` restart lacks MCC arrays, hard-error. Silent reinitialization would invalidate staged states.

## CPU Stress Update Hook

M3b should add a model `3` branch near the current CPU constitutive dispatch:

```text
elastic trial stress -> MCC C++ helper -> updated Sigmac + MCC state
```

The helper should use compression-positive internal variables and convert only at the boundary with `Sigmac`.

## First SPH Smokes

Use the feedback-off explicit-platen T5 workflow:

1. high-`p_c` / overconsolidated elastic-like MCC smoke;
2. mild-yield MCC smoke.

Both:

- CPU Release only;
- `PorePressureFeedback=0`;
- explicit top/bottom platens;
- selected lateral `FlexibleConfiningStress`;
- no GPU;
- no full feedback.

## No-Go Criteria

Stop before broader SPH work if:

- C++ helper parity with M2/M3a is lost;
- `p' <= 0` appears without a clear error path;
- Newton return fails silently;
- MCC state restart is incomplete;
- SPH smoke has `excluded > 0`, DtMin burst, velocity blow-up, or nonphysical `p_c`;
- GPU accepts model `3`.

## Deferred

Deferred beyond M3b:

- full pore-pressure feedback;
- GPU MCC;
- strict paper triaxial reproduction;
- parameter calibration;
- actuator-level reaction diagnostics.
