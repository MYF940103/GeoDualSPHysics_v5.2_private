# M1 MCC XML Parameter Design

## Model Selector

Proposed extension:

```xml
<SoilConstitutiveModel value="3" />
```

Model map:

- `0`: linear elastic skeleton;
- `1`: Drucker-Prager;
- `2`: Drucker-Prager with softening;
- `3`: Modified Cam Clay.

Default behavior must remain unchanged. Existing XML files without `SoilConstitutiveModel=3` should parse and run exactly as before.

## Required MCC Parameters

Recommended XML keys under `<special><soils>`:

```xml
<MccLambda value="..." />
<MccKappa value="..." />
<MccM value="..." />
<MccInitialVoidRatio value="..." />
<MccInitialPreconsolidationPressure value="..." />
```

Alternative to direct `p_c0`:

```xml
<MccOCR value="..." />
```

If OCR is used, the code must compute `p_c0 = OCR * p'_0` after the initial effective stress is known.

## Optional Parameters

```xml
<MccInitialSpecificVolume value="..." />
<MccReferencePressure value="..." />
<MccTensionCutoff value="..." />
<MccIntegrationMode value="1" />
<MccReturnTolerance value="1e-8" />
<MccReturnMaxIter value="25" />
<MccSubstepMax value="0" />
<SaveMccState value="1" />
```

Suggested meanings:

- `MccInitialSpecificVolume`: alternative to `MccInitialVoidRatio`;
- `MccReferencePressure`: optional reference pressure for initialization checks;
- `MccTensionCutoff`: minimum allowed compression-positive `p'`;
- `MccIntegrationMode`: return mapping algorithm selector;
- `MccReturnTolerance`: local yield residual tolerance;
- `MccReturnMaxIter`: Newton iteration limit;
- `MccSubstepMax`: optional local substepping cap;
- `SaveMccState`: output MCC state arrays.

## Validation Rules

For `SoilConstitutiveModel=3`:

- `MccLambda > MccKappa > 0`;
- `MccM > 0`;
- `MccInitialPreconsolidationPressure > 0` or `MccOCR > 0`;
- `MccInitialVoidRatio > -1` or `MccInitialSpecificVolume > 0`;
- `MccTensionCutoff >= 0`;
- `MccReturnTolerance > 0`;
- `MccReturnMaxIter > 0`.

If both `MccInitialVoidRatio` and `MccInitialSpecificVolume` are specified, require:

```text
MccInitialSpecificVolume = 1 + MccInitialVoidRatio
```

within a strict tolerance, or error.

## DP Parameter Isolation

When `SoilConstitutiveModel=3`, DP parameters (`coh`, `phi`, `dlt`, residual strengths, softening exponents) should not control MCC behavior. They may remain in legacy XML for parser compatibility, but logs should state that MCC ignores DP strength parameters.

When `SoilConstitutiveModel=0/1/2`, MCC parameters should have no effect.

## Logging

The startup log should print:

- model name: Modified Cam Clay;
- `lambda`, `kappa`, `M`;
- initial void ratio or specific volume;
- initial `p_c`;
- OCR if used;
- tension cutoff;
- integration mode/tolerance/max iterations;
- CPU-only status;
- restart/output status for MCC arrays.

## GPU Behavior

Until GPU parity is implemented:

```text
SoilConstitutiveModel=3 on GPU -> hard error
```

The error should explain that MCC is CPU-only in the first implementation stage.

## Restart Semantics

Restart should require all MCC state arrays when `SoilConstitutiveModel=3`. If they are absent, the run should error rather than silently reinitializing `p_c` or void ratio. Silent reinitialization would invalidate staged triaxial results.
