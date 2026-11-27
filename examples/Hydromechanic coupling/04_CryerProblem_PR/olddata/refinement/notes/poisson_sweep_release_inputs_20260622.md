# Cryer Poisson-ratio sweep server inputs

Date: 2026-06-22

## Purpose

Prepare server-run XML and GPU BAT files for the Cryer normalized pore-pressure
sequence at several Poisson ratios, matching the u-pw reference comparison
style. The already completed formal run is the `nu=0.3` group.

## Common setup

All new groups are copied from the formal one-stage release configuration:

- `Dp = 0.0025 m`
- `E = 2.0e6 Pa`
- `k = 1e-5 m/s`
- `p0 = 10000 Pa`
- `HydroMechTopLoadMode = 3` (`FlexibleConfinement`)
- `HydroMechDrainage = 1`, `HydroMechDrainageStartTime = 0`
- `HydroMechTopLoadRampTime = 0`
- `SoilDampingCoef = 0.02`
- GPU solver entry, followed by PartVTK and `support/postprocess_cryer.py`
- Postprocess center sampling radius: `r <= 1dp`

## Generated groups

| Poisson ratio | XML | GPU BAT | Tv=1 physical time | output interval |
|---:|---|---|---:|---:|
| 0.1 | `CaseCryerProblem_PR_nu010_Def.xml` | `xCaseCryerProblem_PR_nu010_win64_GPU.bat` | `1.199 s` | `0.001199 s` |
| 0.2 | `CaseCryerProblem_PR_nu020_Def.xml` | `xCaseCryerProblem_PR_nu020_win64_GPU.bat` | `1.103625 s` | `0.001103625 s` |
| 0.45 | `CaseCryerProblem_PR_nu045_Def.xml` | `xCaseCryerProblem_PR_nu045_win64_GPU.bat` | `0.323284090909 s` | `0.000323284090909 s` |

The physical times were recomputed using the same `postprocess_cryer.py`
definition:

`T_v = c_v t / R^2`, with `c_v = k M / (rho_w g)` and
`M = K + 4G/3`.

## Validation

XML parsing succeeded for all three definition files. A GenCase-only check was
also run locally for each group; all three completed with code `0` and produced
the same particle count as the formal `nu=0.3` geometry:

- fixed boundary particles: `8`
- fluid particles: `37173`
- total particles: `37181`

Temporary GenCase check outputs were removed after validation.
