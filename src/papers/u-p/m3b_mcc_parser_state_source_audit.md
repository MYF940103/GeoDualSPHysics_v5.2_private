# M3b MCC Parser / State Source Audit

## Scope

M3b adds Modified Cam Clay parser and state/output infrastructure only. It does not connect the C++ MCC return mapping to the SPH stress update and does not run GPU simulation.

## Parser Path

The soil parser is in `source/JSph.cpp` inside `JSph::InitSoilParameters`.

Current model map:

- `SoilConstitutiveModel=0`: linear elastic skeleton.
- `SoilConstitutiveModel=1`: Drucker-Prager.
- `SoilConstitutiveModel=2`: Drucker-Prager with softening.
- `SoilConstitutiveModel=3`: Modified Cam Clay parser/state skeleton, CPU-only.

The MCC branch reads:

- `MccLambda`;
- `MccKappa`;
- `MccM`;
- `MccInitialVoidRatio` or `MccInitialSpecificVolume`;
- `MccInitialPreconsolidationPressure` or `MccOCR`;
- optional `MccReferencePressure`;
- optional `MccTensionCutoff`;
- optional `MccReturnTolerance`;
- optional `MccReturnMaxIter`;
- optional `SaveMccState`;
- optional reserved `MccStressUpdateEnabled`.

Parser validation is explicit:

- both `e0` and `v0` are rejected;
- neither `e0` nor `v0` is rejected;
- both `pc0` and `OCR` are rejected;
- neither `pc0` nor `OCR` is rejected;
- `lambda <= kappa`, non-positive `M`, non-positive void ratio, invalid `pc0/OCR`, invalid return tolerance, and invalid iteration count all hard-error.

A temporary negative check removed `MccM`; the solver failed clearly with:

```text
Error reading xml - Some element is missing 'MccM'
Finished execution (code=1)
```

## State Storage

CPU state pointers are declared in `source/JSphCpu.h`:

- `MccPcc`;
- `MccVoidRatioc`;
- `MccPlasticVolStrainc`;
- `MccEqPlasticStrainc`;
- `MccYieldFlagc`;
- `MccPlasticMultiplierc`;
- `MccReturnStatusc`;
- `MccReturnIterationsc`;
- `MccYieldResidualc`.

They are independent CPU arrays allocated with `new[]`, not `JArraysCpu` pool arrays. This avoids the fixed per-size pointer limit in `JArraysCpu` when `SavePorePressure` and MCC output are both enabled.

The arrays are:

- allocated when `SoilConstitutiveModel=3` or `SaveMccState=1`;
- sorted with the particle arrays during cell division;
- resized with the existing `SaveArrayCpu` / `RestoreArrayCpu` pattern;
- deleted in `FreeCpuMemoryParticles`.

Boundary/non-material particles receive safe zero/default state values.

## Initialization

MCC initialization is in `source/JSphCpuSingle.cpp`, after stress and pore-pressure field initialization.

For normal material particles:

- `p' = -trace(Sigmac)/3` using current negative-compression `Sigmac`;
- `pc = MccInitialPreconsolidationPressure`, or `pc = OCR * p'`;
- if OCR is requested and `p' <= MccTensionCutoff`, `MccReferencePressure` can supply the reference pressure;
- if no positive reference pressure is available, initialization hard-errors;
- void ratio is taken from `MccInitialVoidRatio` or `MccInitialSpecificVolume - 1`;
- plastic strain diagnostics, yield flag, plastic multiplier, return status, iteration count, and residual are zeroed.

Initialization logs material count and `pc`, void ratio, and initial `p'` statistics.

## Output Skeleton

`source/JSphCpuSingle.cpp::SaveData` now adds MCC fields when `SaveMccState=1`:

- `MccPc`;
- `MccVoidRatio`;
- `MccPlasticVolStrain`;
- `MccEqPlasticStrain`;
- `MccYieldFlag`;
- `MccPlasticMultiplier`;
- `MccReturnStatus`;
- `MccReturnIterations`;
- `MccYieldResidual`.

The temporary save buffers are independent `new[]` arrays, not `JArraysCpu` pool arrays.

## Stress Update Status

`source/JSphCpu.cpp::ApplySoilConstitutiveModelCpu` recognizes model `3`, but M3b intentionally returns the elastic trial stress and keeps `Kplastic` unchanged. The branch logs that MCC stress update is not connected. This prevents silent fallback to DP while keeping parse/init/output smoke tests possible.

Full MCC return mapping remains M3c work.

## Restart Status

M3b does not implement MCC restart loading/saving. Future M3c/M3d work must add restart support for all MCC state arrays and hard-error if model `3` restarts without them.

## GPU Status

`SoilConstitutiveModel=3` hard-errors when `Cpu=false`. GPU Release builds compile, but GPU MCC execution is deferred.
