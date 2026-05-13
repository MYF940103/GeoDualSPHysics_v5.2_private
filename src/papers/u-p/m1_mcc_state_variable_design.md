# M1 MCC State Variable Design

## Required Per-Particle State

Future `SoilConstitutiveModel=3` needs state beyond the current `Sigmac` and `Kplastic` arrays.

Required restart-safe fields:

- `MccPc`: preconsolidation pressure `p_c`;
- `MccVoidRatio` or `MccSpecificVolume`: choose one primary storage variable;
- `MccPlasticVolStrain`: accumulated compression-positive plastic volumetric strain;
- `MccPlasticShearStrain` or `MccEqPlasticStrain`: optional but useful for diagnostics;
- `MccYieldFlag`: saved/output flag indicating elastic or plastic step;
- `MccPlasticMultiplier`: last-step plastic multiplier for diagnostics;
- `MccReturnStatus`: optional convergence/fallback code.

Recommended primary storage:

```text
MccPc
MccVoidRatio
MccPlasticVolStrain
MccEqPlasticStrain
MccYieldFlag
MccPlasticMultiplier
```

Specific volume can be computed as `v = 1 + e`.

## Temporary Variables

Temporary variables do not need restart storage:

- trial `p'`;
- trial `q`;
- trial deviatoric stress;
- Newton residual;
- Newton derivative/Jacobian entries;
- iteration count, unless saved as a diagnostic.

## Relationship to Kplastic

`Kplastic` is currently a DP-style accumulated deviatoric plastic measure. It should not be reused as `p_c`, void ratio, or volumetric plastic strain.

Recommended approach:

- keep `Kplastic` as a generic legacy plastic measure/output;
- for MCC, set `Kplastic` to an equivalent plastic strain only for broad visualization compatibility;
- store true MCC variables in MCC-specific arrays.

This avoids breaking DP postprocessing while making MCC state explicit.

## Restart Requirements

The following must be stored and restored for a stress-consistent MCC restart:

- `Sigma_kk`;
- `Sigma_ij`;
- `PorePress` when hydromechanics is active;
- `MccPc`;
- `MccVoidRatio` or `MccSpecificVolume`;
- `MccPlasticVolStrain`;
- `MccEqPlasticStrain`;
- optional diagnostic flags if a staged restart needs exact reporting.

`Kplastic` alone is insufficient for MCC.

## Output Requirements

Minimum output for early validation:

- `MccPc`;
- `MccVoidRatio` or `MccSpecificVolume`;
- `MccPlasticVolStrain`;
- `MccEqPlasticStrain`;
- `MccYieldFlag`;
- `MccPlasticMultiplier`;
- `Kplastic` for compatibility.

Postprocessing should compute:

- `p'`;
- `q`;
- `eta = q / p'`;
- yield residual `f`;
- plastic particle count.

## Initialization

Initialization options should support:

- direct `MccInitialPreconsolidationPressure`;
- OCR-based initialization:

```text
p_c0 = OCR * p'_0
```

- direct `MccInitialVoidRatio`;
- direct `MccInitialSpecificVolume`.

At least one of void ratio or specific volume must be provided. If both are provided, the parser should error unless they are exactly consistent.

## Memory Impact

A minimal CPU implementation adds roughly 5 to 7 scalar arrays per particle. If stored as `float`, this is about 20 to 28 bytes per particle. If stored as `double`, this is about 40 to 56 bytes per particle.

Recommendation:

- use `double` inside the local return mapping;
- store per-particle state as `float` initially only if accuracy checks pass;
- consider `double` storage for `p_c` and void ratio if single-point tests show drift.

## CPU First, GPU Later

CPU arrays, restart, and output should be implemented first. GPU support requires:

- mirrored device arrays;
- device return mapping;
- GPU restart/sort integration;
- GPU output support;
- hard-error removal only after parity tests.

Until then, `SoilConstitutiveModel=3` should hard-error on GPU.
