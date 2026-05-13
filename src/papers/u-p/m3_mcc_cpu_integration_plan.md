# M3 MCC CPU Integration Plan

## Objective

M3 should port the verified M2 standalone MCC return mapping into the CPU solver as an opt-in `SoilConstitutiveModel=3` path. It should remain CPU-only and feedback-off for the first SPH smokes.

## Likely Files Touched

Expected source areas:

- `source/DualSphDef.h`: extend `StSoilCte` with MCC constants;
- `source/JSph.cpp`: parse and validate MCC XML parameters;
- `source/JSph.h`: add MCC configuration/state declarations if needed;
- `source/JSphCpu.h`: add CPU MCC state arrays;
- `source/JSphCpu.cpp`: allocate/free/sort/save arrays and add CPU constitutive branch;
- `source/JSphCpuSingle.cpp`: initialize, restart, sort, and output MCC state;
- `source/JPartsLoad4.*`: load MCC restart arrays;
- output writer path: add optional MCC state fields.

GPU source should only receive a hard error for `SoilConstitutiveModel=3` until a later GPU port.

## Parser Integration

Extend model selector:

```text
0 = linear elastic skeleton
1 = Drucker-Prager
2 = Drucker-Prager softening
3 = Modified Cam Clay
```

Required XML keys for model `3`:

- `MccLambda`;
- `MccKappa`;
- `MccM`;
- `MccInitialVoidRatio` or `MccInitialSpecificVolume`;
- `MccInitialPreconsolidationPressure` or `MccOCR`;
- `MccTensionCutoff`;
- `MccReturnTolerance`;
- `MccReturnMaxIter`;
- `SaveMccState`.

Validation:

- `lambda > kappa > 0`;
- `M > 0`;
- `p_c0 > 0` or valid OCR;
- void ratio/specific volume valid;
- GPU run with model `3` hard-errors.

## MCC State Arrays

Minimum CPU arrays:

- `MccPcc`;
- `MccVoidRatioc` or `MccSpecificVolumec`;
- `MccPlasticVolStrainc`;
- `MccEqPlasticStrainc`;
- `MccYieldFlagc`;
- `MccPlasticMultiplierc`;
- optional `MccReturnStatusc` / `MccReturnIterationsc` diagnostics.

Do not overload `Kplastic` as the only MCC state. `Kplastic` may be filled as a compatibility equivalent plastic measure for plots.

## Initialization

Initialization should:

1. initialize stress through the existing `Sigmac` path;
2. compute initial compression-positive `p' = -trace(Sigmac)/3`;
3. initialize `p_c` directly or via `OCR * p'`;
4. initialize void ratio/specific volume;
5. zero MCC plastic strain diagnostics.

If `p' <= MccTensionCutoff`, error for the first implementation.

## CPU Stress Update Branch

Add a model `3` branch in `ApplySoilConstitutiveModelCpu` or a nearby helper:

```text
sigma_e, MCC old state -> MCC return mapping -> signew, MCC new state
```

M3 should port the M2 four-variable local Newton return mapping into C++ and run local calculations in double precision.

The branch must convert:

```text
Sigmac stored negative compression <-> MCC internal positive compression
```

at a single well-documented interface.

## Output Fields

When `SaveMccState=1`, output:

- `MccPc`;
- `MccVoidRatio` or `MccSpecificVolume`;
- `MccPlasticVolStrain`;
- `MccEqPlasticStrain`;
- `MccYieldFlag`;
- `MccPlasticMultiplier`;
- optional `MccReturnIterations`.

Postprocessing should continue to output `p'`, `q`, and reaction diagnostics from existing scripts.

## Restart Fields

Restart must restore:

- `Sigma_kk`;
- `Sigma_ij`;
- `Kplastic`;
- `PorePress` when active;
- all required MCC state arrays.

If MCC arrays are missing in a model `3` restart, error rather than silently reinitializing.

## First SPH Tests

Use the T5 feedback-off explicit-platen workflow:

1. MCC high-`p_c` / overconsolidated elastic-like smoke:
   - `PorePressureFeedback=0`;
   - lateral `FlexibleConfiningStress` selected;
   - explicit top/bottom platens;
   - CPU Release only.
2. MCC mild-yield smoke:
   - same setup;
   - parameters chosen to activate plasticity mildly.

Do not run GPU. Do not enable full feedback.

## No-Go Criteria

Stop M3 if:

- C++ single-point parity fails against M2 Python output;
- `p' <= 0` appears without an explicit handled diagnostic;
- MCC Newton return fails silently;
- restart loses MCC state;
- first SPH smoke has `excluded > 0`, DtMin burst, velocity blow-up, or nonphysical `p_c`;
- GPU accepts model `3` before implementation.

## Deferred Items

Deferred beyond M3:

- full pore-pressure feedback;
- GPU MCC;
- strict paper triaxial reproduction;
- MCC parameter calibration;
- actuator-level platen reaction.
