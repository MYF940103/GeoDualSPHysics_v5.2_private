# C5q Cryer Experimental Interface Inventory

Date: 2026-05-13

This is a documentation-only inventory. No source code, GenCase output, CPU/GPU
run, or PartVTK processing was performed.

## Source Map

The Cryer-related interfaces are concentrated in these files:

- `source/DualSphDef.h`: soil constant storage, including
  `SoilConstitutiveModel`.
- `source/JSph.h`: execution parameter storage for hydraulic boundary,
  confining stress, shell, MLS, and limiter controls.
- `source/JSph.cpp`: defaults, XML execution-parameter parsing, validation,
  and logging.
- `source/JSphCpu.cpp`: CPU pore-pressure boundary operator implementation,
  flexible confining stress contribution, and CPU soil constitutive switch.
- `source/JSphCpuSingle.cpp`: CPU pressure update sequence and application of
  `PorePressureBoundaryOperator`.
- `source/JSphGpu.cpp`, `source/JSphGpu_ker.cu`, `source/JSphGpuSimple_ker.cu`:
  GPU support for the older PR boundary operator and soil model, plus hard
  errors for CPU-only Cryer routes.

## Constitutive Interface

| Interface | XML name | Default | Source / parser | CPU/GPU path | Related experiments | Recommendation |
|---|---|---:|---|---|---|---|
| Linear/DP/softening switch | `<SoilConstitutiveModel value="..."/>` under `<special><soils>` | If absent: `1`, or `2` when legacy `Softening=1` is present | `source/DualSphDef.h`; parser `source/JSph.cpp:3988-3998`; validation `source/JSph.cpp:4072-4073` | CPU `source/JSphCpu.cpp:4922`; GPU `source/JSphGpuSimple_ker.cu:418` | E1, C4-C through C5o, 1D elastic switch | Keep stable |
| Legacy softening compatibility | `<Softening value="..."/>` | `0` | `source/JSph.cpp:3988-3998` | CPU/GPU through same soil constants | Pre-existing DP softening and E1 | Keep stable |

`SoilConstitutiveModel=0` is not a Cryer-only artifact. It is useful for
poroelastic, triaxial, and confinement benchmarks.

## Hydraulic Representation

| Interface | XML name | Default | Source / parser | CPU/GPU path | Related experiments | Recommendation |
|---|---|---:|---|---|---|---|
| Elevation source switch | `HydraulicElevationSource` | `1` | default `source/JSph.cpp:237`; parser `source/JSph.cpp:926-929`; GPU hard error `source/JSph.cpp:1008-1009` | CPU pressure convention in `JSphCpuSingle.cpp`; GPU unsupported for `0` | C4-D, C5 strict route | Keep stable CPU feature, experimental GPU status |
| Hydraulic gravity vector | `HydraulicGravityX/Y/Z` | `0,0,0` with fallback to body gravity | default `source/JSph.cpp:254`; parser `source/JSph.cpp:975-977`; magnitude helper `source/JSph.cpp` | CPU/GPU general hydromech scaling | All hydromech benchmarks | Keep stable |
| Hydraulic gravity magnitude | no separate XML parameter found | derived | `GetHydraulicGmag()` uses hydraulic vector/body gravity | CPU/GPU | C4-D notes | No cleanup needed |

`HydraulicElevationSource=0` is needed to express gravity-free pressure
diffusion. It remains CPU-only in this branch, but it should not be removed
because it may serve non-Cryer diffusion tests.

## Mechanical Loading Interface

| Interface | XML name | Default | Source / parser | CPU/GPU path | Related experiments | Recommendation |
|---|---|---:|---|---|---|---|
| Flexible confining stress switch | `FlexibleConfiningStress` | `0` | storage `source/JSph.h:268`; default `source/JSph.cpp:257`; parser `source/JSph.cpp:979-982`; validation `source/JSph.cpp:1056-1058` | CPU pair contribution `source/JSphCpu.cpp:1110-1443`; GPU hard error `source/JSphGpu.cpp:1433` | C4-B3/C4-B4, Cryer compression diagnostics | Keep stable CPU experimental |
| Compression magnitude | `ConfiningStressP0` | `0` | parser `source/JSph.cpp:984`; validation `source/JSph.cpp:1052` | CPU only with `FlexibleConfiningStress=1` | C4-B4, C5 compression cases | Keep stable CPU experimental |
| Ramp start/end | `ConfiningStressRampStart`, `ConfiningStressRampEnd` | `0`, start | parser `source/JSph.cpp:985-986`; ramp helper `source/JSph.cpp:3219-3229` | CPU only | C4-B4, C5 compression cases | Keep stable CPU experimental |
| Target marker | `ConfiningStressTargetMk` | `-1` | parser `source/JSph.cpp:987`; target helper `source/JSph.cpp:3235-3238` | CPU only | C4-B4, C5 | Keep stable CPU experimental |
| Mode | `ConfiningStressMode` | `0` | parser `source/JSph.cpp:988-990`; only mode 0 implemented | CPU only | C4-B4, C5 | Keep stable CPU experimental |

The confining stress route is not validated as final Cryer loading, but it is a
reusable loading candidate for triaxial and confinement baselines.

## Pore-Pressure Boundary Entry Points

| Interface | XML name | Default | Source / parser | CPU/GPU path | Related experiments | Recommendation |
|---|---|---:|---|---|---|---|
| Boundary operator selector | `PorePressureBoundaryOperator` | `0` | default `source/JSph.cpp:199`; parser `source/JSph.cpp:777-788` | Mode `0` default; mode `1` CPU/GPU; mode `2` CPU-only; mode `3` CPU-only | B1/B5/H1, Cryer C4-C through C5o | Keep experimental selector; mode `0` remains production default |
| Curved drained enable | `PorePressureCurvedDrained` | `0` | default `source/JSph.cpp:200`; parser `source/JSph.cpp:790-793`; validation `source/JSph.cpp:1010-1014` | CPU-only with operator `3`; GPU hard error | C4-C through C5o | Keep experimental |
| Sphere center | `CurvedDrainedBoundaryCenterX/Y/Z` | `0,0,0` | default `source/JSph.cpp:201`; parser `source/JSph.cpp:795-797` | CPU curved operator | C4-C through C5o | Keep experimental |
| Sphere radius | `CurvedDrainedBoundaryRadius` | `0` | default `source/JSph.cpp:202`; parser `source/JSph.cpp:798`; validation `source/JSph.cpp:1015-1016` | CPU curved operator | C4-C through C5o | Keep experimental |
| Material target marker | `CurvedDrainedBoundaryTargetMk` | `-1` | default `source/JSph.cpp:203`; parser `source/JSph.cpp:799` | CPU curved operator | C4-C through C5o | Keep experimental |
| Boundary value | `CurvedDrainedBoundaryValue` | `0` | default `source/JSph.cpp:204`; parser `source/JSph.cpp:800` | CPU curved operator | C4-C through C5o | Keep experimental |
| Excess/total convention | `CurvedDrainedBoundaryUseExcess` | `1` | default `source/JSph.cpp:205`; parser `source/JSph.cpp:801-805` | CPU curved operator | C4-C through C5o | Keep experimental |
| Boundary thickness | `CurvedDrainedBoundaryThickness` | `0` | default `source/JSph.cpp:206`; parser `source/JSph.cpp:806`; validation `source/JSph.cpp:1019-1020` | CPU curved operator | C4-C through C5o | Keep experimental |
| Curved mode selector | `CurvedDrainedBoundaryMode` | `0` | default `source/JSph.cpp:207`; parser `source/JSph.cpp:807-817` | CPU only for curved route; GPU hard error via operator `3` | C4-C through C5o | Keep but mark modes `5-8` deprecated |
| Boundary target marker | `CurvedDrainedBoundaryTargetMkBound` | `-1` | default `source/JSph.cpp:208`; parser `source/JSph.cpp:819` | Mode `4` CPU | C5e/C5f | Keep experimental |
| Boundary-particle enable | `CurvedDrainedBoundaryUseBoundaryParticles` | `1` | default `source/JSph.cpp:209`; parser `source/JSph.cpp:820-824`; mode-4 validation `source/JSph.cpp:1025-1026` | Mode `4` CPU | C5e/C5f | Keep experimental |
| Selection tolerance | `CurvedDrainedBoundarySelectionTolerance` | `0` | default `source/JSph.cpp:210`; parser `source/JSph.cpp:825`; validation `source/JSph.cpp:1023-1024` | Mode `4` CPU | C5e through C5i | Keep experimental |
| Adami diagnostic | `CurvedDrainedBoundaryAdamiDiagnostic` | `0` | default `source/JSph.cpp:211`; parser `source/JSph.cpp:826-830` | Mode `4` CPU diagnostics | C5f | Keep experimental diagnostic |
| Boundary weighting | `CurvedDrainedBoundaryWeighting` | `0` | default `source/JSph.cpp:212`; parser `source/JSph.cpp:831-835` | Mode `4` CPU; warning if used by modes `5-8` | C5f through C5i | Keep experimental `0/1`; mark `3` diagnostic |

No generic XML parameter named `CurvedDrainedBoundaryDiagnostics` was found.
The implementation instead has more specific diagnostics controls listed below.

## Failed or Archived Correction Parameters

| Interface | XML name | Default | Source / parser | CPU/GPU path | Related experiments | Recommendation |
|---|---|---:|---|---|---|---|
| Flux diagnostics | `CurvedDrainedFluxDiagnostics` | `0` | default `source/JSph.cpp:215`; parser `source/JSph.cpp:843-846` | CPU modes `5/6/7` logging | C5j/C5k/C5m | Deprecate with modes `5-7` |
| Mode-5 MLS order | `CurvedDrainedMLSOrder` | `1` | default `source/JSph.cpp:213`; parser `source/JSph.cpp:837-840` | CPU mode `5` | C5j; carried into some C5k/C5m XML | Deprecate/archive |
| Mode-5 MLS radius | `CurvedDrainedMLSRadiusFactor` | `1` | default `source/JSph.cpp:214`; parser `source/JSph.cpp:842` | CPU mode `5` | C5j | Deprecate/archive |
| Mode-5 condition limit | `CurvedDrainedMLSConditionLimit` | `1e8` | default `source/JSph.cpp:216`; parser `source/JSph.cpp:848` | CPU mode `5` | C5j | Deprecate/archive |
| Mode-5 fallback | `CurvedDrainedMLSFallbackMode` | `3` | default `source/JSph.cpp:217`; parser `source/JSph.cpp:849-852` | CPU mode `5` | C5j | Deprecate/archive |
| Mode-7 shell count | `CurvedDrainedShellCount` | `0` | default `source/JSph.cpp:218`; parser `source/JSph.cpp:855-857` | CPU mode `7` | C5m | Deprecate/archive |
| Mode-7 min particles | `CurvedDrainedShellMinParticles` | `1` | default `source/JSph.cpp:219`; parser `source/JSph.cpp:860-862` | CPU mode `7` | C5m | Deprecate/archive |
| Mode-7 shell mode | `CurvedDrainedShellMode` | `0` | default `source/JSph.cpp:220`; parser `source/JSph.cpp:864-867` | CPU mode `7` | C5m | Deprecate/archive |
| Mode-7 correction mode | `CurvedDrainedShellCorrectionMode` | `1` | default `source/JSph.cpp:221`; parser `source/JSph.cpp:869-872` | CPU mode `7` | C5m | Deprecate/archive |
| Mode-7 diagnostics | `CurvedDrainedShellDiagnostics` | `0` | default `source/JSph.cpp:222`; parser `source/JSph.cpp:874-877` | CPU mode `7` | C5m | Deprecate/archive |
| Mode-8 support radius | `CurvedDrainedCorrectedLapRadiusFactor` | `2` | default `source/JSph.cpp:223`; parser `source/JSph.cpp:879` | CPU mode `8` | C5n/C5o | Deprecate/archive |
| Mode-8 radial threshold | `CurvedDrainedCorrectedLapRMinFactor` | `0.7` | default `source/JSph.cpp:224`; parser `source/JSph.cpp:880` | CPU mode `8` | C5n/C5o | Deprecate/archive |
| Mode-8 boundary samples | `CurvedDrainedCorrectedLapBoundarySamples` | `9` | default `source/JSph.cpp:225`; parser `source/JSph.cpp:882-884` | CPU mode `8` | C5n/C5o | Deprecate/archive |
| Mode-8 min samples | `CurvedDrainedCorrectedLapMinSamples` | `12` | default `source/JSph.cpp:226`; parser `source/JSph.cpp:887-889` | CPU mode `8` | C5n/C5o | Deprecate/archive |
| Mode-8 condition limit | `CurvedDrainedCorrectedLapConditionLimit` | `1e12` | default `source/JSph.cpp:227`; parser `source/JSph.cpp:891` | CPU mode `8` | C5n/C5o | Deprecate/archive |
| Mode-8 boundary weight | `CurvedDrainedCorrectedLapBoundaryWeight` | `1` | default `source/JSph.cpp:228`; parser `source/JSph.cpp:892` | CPU mode `8` | C5n/C5o | Deprecate/archive |
| Mode-8 fallback | `CurvedDrainedCorrectedLapFallbackMode` | `0` | default `source/JSph.cpp:229`; parser `source/JSph.cpp:893-896` | CPU mode `8` | C5n/C5o | Deprecate/archive |
| Mode-8 diagnostics | `CurvedDrainedCorrectedLapDiagnostics` | `0` | default `source/JSph.cpp:230`; parser `source/JSph.cpp:898-901` | CPU mode `8` | C5n/C5o | Deprecate/archive |
| Mode-8 limiter selector | `CurvedDrainedCorrectedLaplacianLimiter` | `0` | default `source/JSph.cpp:231`; parser `source/JSph.cpp:903-907` | CPU mode `8` | C5o | Deprecate/archive |
| Mode-8 limiter CFL | `CurvedDrainedLimiterCFL` | `0.9` | default `source/JSph.cpp:232`; parser `source/JSph.cpp:909` | CPU mode `8` | C5o | Deprecate/archive |
| Mode-8 blend | `CurvedDrainedLimiterBlend` | `1` | default `source/JSph.cpp:233`; parser `source/JSph.cpp:910` | CPU mode `8` | C5o | Deprecate/archive |
| Mode-8 post-blend cap | `CurvedDrainedLimiterPreventNegative` | `0` | default `source/JSph.cpp:234`; parser `source/JSph.cpp:911-914` | CPU mode `8` | C5o | Deprecate/archive |

## Mode Inventory

| Mode | Meaning | Final C5 status | Recommendation |
|---:|---|---|---|
| `0` | First-order spherical Dirichlet ghost | Not enough for strict Cryer, but simple baseline | Keep experimental |
| `1` | Strengthened image ghost | Small improvement only | Keep experimental but not recommended |
| `2` | Diagnostic material clamp | Not production | Deprecate as diagnostic only |
| `3` | Multi-sample material-side quadrature | Failed to solve surface residual | Deprecate/archive |
| `4` | Boundary-particle prescribed drained state | Conceptually useful, but not FV-gate validated | Keep experimental, not validated |
| `5` | MLS normal-gradient flux correction | Failed FV gate | Deprecate/archive |
| `6` | Radial-shell boundary flux | Failed FV gate | Deprecate/archive |
| `7` | Conservative shell exchange | Failed FV gate | Deprecate/archive |
| `8` | Corrected MLS Laplacian plus limiters | Manufactured gate useful, dynamic gate failed | Deprecate/archive |

## Summary Recommendation

Keep the general-purpose interfaces (`SoilConstitutiveModel`,
`HydraulicElevationSource`, `FlexibleConfiningStress`) and keep the boundary
operator entry points as experimental documentation. Mark modes `5-8` and
their specific parameters as archived failed Cryer research paths. Do not
delete source in C5q.
