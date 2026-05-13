# T4k Initial Hydrostatic Effective Stress Source Audit

## Purpose

T4k checks whether the reduced triaxial specimen can be placed closer to a Zhao-style pre-confined state before pore-pressure feedback and axial loading are applied. The audit focused on the existing CPU stress state, XML support, sign convention, restart behavior, and GPU status.

## Current Source Mapping

| Item | Finding |
|---|---|
| Stress tensor storage | CPU material skeleton/effective stress is stored in `Sigmac` as `tsymatrix3f` (`Sigma_kk` and `Sigma_ij` in saved output). |
| Initialization location | `Sigmac` and `Kplasticc` are zeroed in `JSphCpuSingle::ConfigDomain()` before the time loop. Restart files can restore `Sigma_kk`, `Sigma_ij`, and `Kplastic`. |
| Constitutive update | `GetStressRateTensor_Elastic()` updates `Sigmac` from the strain-rate tensor. Compression strain produces negative diagonal stress in the current code convention. |
| Existing XML support | No general initial-stress XML interface existed before T4k. Old commented self-weight initialization lines existed but were not active. |
| Per-mk support | Flexible confinement already uses `ConfiningStressTargetMk`; T4k adds an analogous initial-stress target mk. |
| Pore pressure | Initial effective stress does not initialize or modify `PorePress`; it is strictly a skeleton/effective stress initialization. |
| GPU | Initial stress is CPU-only in T4k. Non-default use on GPU is a hard error. GPU build still compiles the parser path. |

## Implemented Interface

T4k adds:

| Parameter | Default | Meaning |
|---|---:|---|
| `InitialStressMode` | `0` | `0`: none. `1`: uniform isotropic effective compression. |
| `InitialEffectiveStressIso` | `0` | Positive compression magnitude in Pa. |
| `InitialEffectiveStressTargetMk` | `-1` | `-1`: all normal material particles; otherwise matching `mkfluid` type value. |

Default behavior is unchanged because `InitialStressMode=0`.

## Sign Convention

The XML input is a positive compression magnitude, but CPU `Sigmac` stores compressive skeleton/effective stress as negative diagonal stress. Therefore:

```text
InitialEffectiveStressIso = 50 Pa
Sigmac.xx = Sigmac.yy = Sigmac.zz = -50 Pa
```

This follows the active elastic stress-rate convention, where compressive strain gives negative stress. It is distinct from `ConfiningStressP0`, which is a positive external compression source that is not written into `Sigmac`.

## Insertion Point

The initial stress is applied after `LoadCodeParticles()` in `JSphCpuSingle::ConfigDomain()`, before pore-pressure boundary initialization and before the time loop. This allows `mk` filtering from `Codec` while preserving the existing restart priority:

- new runs: initialize selected target material particles;
- restart runs: skip `InitialStressMode=1` and preserve restored `Sigma_kk` / `Sigma_ij`.

## Diagnostics

When enabled, the CPU log reports:

- target particle count;
- code diagonal value written to `Sigmac`;
- mean `sigma_xx/sigma_yy/sigma_zz`;
- diagonal ranges;
- mean `q` proxy and deviatoric norm.

Saved `PartCsv` output also contains the initialized `Sigma_kk` / `Sigma_ij` fields for postprocessing.

## Limitations

This is an initial effective-stress field only. It does not yet provide:

- cap boundary traction or axial hydrostatic loading;
- total-stress coupling;
- restart-stage stress equilibration;
- GPU execution;
- a production triaxial initialization workflow.

The reduced free-surface cylinder can still emit stress waves if the initialized effective stress is not balanced by matching external boundary traction on all relevant surfaces.
