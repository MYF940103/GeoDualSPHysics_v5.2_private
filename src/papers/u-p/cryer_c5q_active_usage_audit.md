# C5q Active Usage Audit

Date: 2026-05-13

This audit used repository text search only. No simulations or generated output
were run. The untracked `C5i_Dp005FullTimeLongRun/` directory was observed by
search/status but was not modified.

## Usage Categories

- Active/default production examples: current launch examples and non-Cryer
  u-pw workflows using default or previously validated paths.
- Archived Cryer C5 experiments: files under
  `examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/`.
- Future planned benchmarks: T1 triaxial, L2 1D external-load extension, slope
  work. These are plan references, not active XML dependencies.
- Docs-only references: reports, notes, and parameter documentation.

## Interface Usage Table

| Parameter / mode | Used in source? | Used in active example? | Used only in archived C5 experiments? | Used in docs? | Safe to remove now? | Deprecation action |
|---|---|---|---|---|---|---|
| `SoilConstitutiveModel` | Yes, CPU and GPU soil update | Yes, 1D elastic switch and Cryer XML | No | Yes | No | Keep stable |
| `HydraulicElevationSource` | Yes, CPU parser/update; GPU hard error for `0` | No broad production use found; Cryer strict uses `0` | Mostly Cryer C4-D/C5 | Yes | No | Keep stable CPU experimental |
| `HydraulicGravityX/Y/Z` | Yes | Yes, hydromech examples | No | Yes | No | Keep stable |
| `FlexibleConfiningStress` | Yes, CPU only; GPU hard error | No default production example found | Cryer C4-B/C5 | Yes | No | Keep stable CPU experimental |
| `ConfiningStressP0/Ramp/TargetMk/Mode` | Yes | No default production example found | Cryer C4-B/C5 | Yes | No | Keep with `FlexibleConfiningStress` |
| `PorePressureBoundaryOperator=0` | Yes | Yes, default Cryer baseline, 1D, self-weight | No | Yes | No | Production default |
| `PorePressureBoundaryOperator=1` | Yes | Yes, B1/B4/B5 self-weight experiments | No | Yes | No | Keep experimental, GPU-supported |
| `PorePressureBoundaryOperator=2` | Yes | Yes, H1 self-weight experiments | No | Yes | No | Keep experimental CPU-only |
| `PorePressureBoundaryOperator=3` | Yes | No active production example outside Cryer strict plan | Yes | Yes | No | Keep experimental entry point; mark strict Cryer failed |
| `PorePressureCurvedDrained` | Yes | No active production example outside Cryer strict plan | Yes | Yes | No | Keep experimental |
| Curved common geometry/value parameters | Yes | No active production example outside Cryer strict plan | Yes | Yes | No | Keep experimental |
| `CurvedDrainedBoundaryMode=0` | Yes | Cryer draft/archived only | Yes | Yes | No | Keep experimental baseline |
| `CurvedDrainedBoundaryMode=1` | Yes | No | Yes | Yes | No | Keep but not recommended |
| `CurvedDrainedBoundaryMode=2` | Yes | No | Yes | Yes | No | Deprecate diagnostic clamp |
| `CurvedDrainedBoundaryMode=3` | Yes | No | Yes | Yes | No | Deprecate/archive |
| `CurvedDrainedBoundaryMode=4` | Yes | No active production example outside Cryer strict plan | Yes | Yes | No | Keep experimental, not validated |
| `CurvedDrainedBoundaryWeighting=0/1` | Yes | No active production example outside Cryer strict plan | Yes | Yes | No | Keep with mode `4`, experimental |
| `CurvedDrainedBoundaryWeighting=3` | Yes | No | Yes | Yes | No | Deprecate diagnostic capped weighting |
| Mode-5 `CurvedDrainedMLS*` | Yes | No | Yes, C5j and carried into later XML | Yes | Not now | Deprecate/archive |
| `CurvedDrainedFluxDiagnostics` | Yes | No | Yes | Yes | Not now | Deprecate with modes `5-7` |
| Mode-7 `CurvedDrainedShell*` | Yes | No | Yes, C5m | Yes | Not now | Deprecate/archive |
| Mode-8 `CurvedDrainedCorrectedLap*` | Yes | No | Yes, C5n/C5o | Yes | Not now | Deprecate/archive |
| Mode-8 limiter parameters | Yes | No | Yes, C5o | Yes | Not now | Deprecate/archive |

## XML Usage Findings

The active reduced Cryer baseline still uses:

- `PorePressureBoundaryOperator=0`.

Non-Cryer u-pw examples use:

- `PorePressureBoundaryOperator=0` in the default production-style cases;
- `PorePressureBoundaryOperator=1` in B1/B4/B5 boundary-operator experiments;
- `PorePressureBoundaryOperator=2` in H1 hydraulic mDBC experiments.

Cryer strict archived experiments use:

- `PorePressureBoundaryOperator=3`;
- `PorePressureCurvedDrained=1`;
- `CurvedDrainedBoundaryMode=0-8`;
- mode-specific MLS, shell, corrected-Laplacian, and limiter parameters.

No active non-Cryer XML dependency on `CurvedDrainedBoundaryMode=5/6/7/8` was
found.

## Source Usage Findings

All parameters remain parsed by `source/JSph.cpp`. The CPU implementation for
curved drained modes is in `source/JSphCpu.cpp`, called by
`source/JSphCpuSingle.cpp` only when hydromechanical PR pressure is active.

GPU support:

- `SoilConstitutiveModel` is supported on CPU and GPU.
- `PorePressureBoundaryOperator=1` is supported on CPU and GPU.
- `PorePressureBoundaryOperator=2`, `PorePressureBoundaryOperator=3`,
  `PorePressureCurvedDrained=1`, `HydraulicElevationSource=0`, and
  `FlexibleConfiningStress=1` hard-error on GPU.

## Removal Risk

No parameter is recommended for immediate deletion in C5q. Even failed Cryer
interfaces are still referenced by archived XML cases, reports, and parameter
documentation. Removing them now would make the C5 evidence chain harder to
reproduce and would risk collateral changes before T1.

The safe action now is documentation deprecation, not source deletion.
