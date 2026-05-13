# M3b MCC Parser / State Initialization Report

## Objective

M3b wires Modified Cam Clay parser, CPU state arrays, initialization, and output fields into GeoDualSPHysics without enabling the MCC stress return mapping.

No full MCC SPH validation, full pore-pressure feedback, Cryer case, or GPU simulation was run.

## Source Changes

Implemented:

- `SoilConstitutiveModel=3` parser recognition.
- MCC XML parameter parsing and validation.
- CPU-only MCC state arrays.
- MCC state initialization from either `pc0` or `OCR`.
- `SaveMccState` output skeleton.
- GPU hard error for model `3`.
- Explicit CPU model `3` pass-through in `ApplySoilConstitutiveModelCpu`.

Not implemented:

- MCC return mapping inside SPH stress update.
- MCC restart support.
- GPU MCC arrays or kernels.

## XML Parameters

Required for `SoilConstitutiveModel=3`:

- `MccLambda`;
- `MccKappa`;
- `MccM`;
- one of `MccInitialVoidRatio` or `MccInitialSpecificVolume`;
- one of `MccInitialPreconsolidationPressure` or `MccOCR`.

Optional:

- `MccReferencePressure`;
- `MccTensionCutoff`;
- `MccReturnTolerance`;
- `MccReturnMaxIter`;
- `SaveMccState`;
- reserved `MccStressUpdateEnabled`.

Default behavior is unchanged for existing models `0/1/2`.

## Smoke Cases

Retained under:

```text
examples/u-pw/04_Undrained_Triaxial/experiments/M3b_MCCParserStateInit/
```

| Case | Purpose | Result |
| --- | --- | --- |
| `CaseM3b_MccPc0_Init` | direct `pc0=200 Pa`, no initial stress | `code=0`, `excluded=0`, `DtMin=0` |
| `CaseM3b_MccOCR_InitialStress` | `OCR=4` with `InitialEffectiveStressIso=50 Pa` | `code=0`, `excluded=0`, `DtMin=0` |

Both cases use:

- `SoilConstitutiveModel=3`;
- `SaveMccState=1`;
- `PorePressureFeedback=0`;
- extremely short CPU Release smoke.

## Initialization Metrics

Generated CSV:

- `m3b_case_summary.csv`;
- `m3b_mcc_state_initialization_metrics.csv`.

Initial saved frame:

| Case | Material particles | `pc_mean` | `e_mean` | `p'_mean` | Plastic diagnostics |
| --- | ---: | ---: | ---: | ---: | --- |
| `CaseM3b_MccPc0_Init` | `407` | `200 Pa` | `0.8` | `0 Pa` | zero |
| `CaseM3b_MccOCR_InitialStress` | `407` | `200 Pa` | `0.8` | `50 Pa` | zero |

The OCR case confirms the sign mapping:

```text
InitialEffectiveStressIso=50 Pa -> Sigmac.xx=Sigmac.yy=Sigmac.zz=-50 Pa -> p'=+50 Pa
OCR=4 -> pc=200 Pa
```

Final saved-frame `p'` changes in the OCR case because M3b still lets the solver take one elastic pass-through step. That is a smoke-test artifact, not an MCC plastic update.

## Missing Parameter Check

A temporary negative XML removed `MccM`. The solver failed before running:

```text
Error reading xml - Some element is missing 'MccM'
Finished execution (code=1)
```

This confirms missing required MCC parameters produce a clear error.

## Output

`SaveMccState=1` writes these PartCsv fields:

- `MccPc`;
- `MccVoidRatio`;
- `MccPlasticVolStrain`;
- `MccEqPlasticStrain`;
- `MccYieldFlag`;
- `MccPlasticMultiplier`;
- `MccReturnStatus`;
- `MccReturnIterations`;
- `MccYieldResidual`.

The smoke PartCsv headers include all fields.

## Build

Builds:

- CPU Release: passed.
- GPU Release: passed.

GPU simulation was not run. Model `3` remains hard-deferred on GPU.

## Assessment

M3b parser, state allocation, initialization, and output skeleton are in place. MCC stress update is still not connected, and this is intentional.

M3c can now implement the CPU MCC stress update branch using the verified C++ helper from M3a.

Full pore-pressure feedback and GPU remain deferred.
