# 06 Sainte-Monique

This directory tracks the u-pw PR reproduction path for the Sainte-Monique
field landslide case.

No validated field geometry, material zoning, or calibration data are currently
available in this repository. The runnable XML here is therefore a reduced
placeholder smoke case only. It is not a Sainte-Monique reproduction.

## Files

- `data/README.md`  
  Documents the missing field data required for a validated reproduction.
- `CaseSainteMonique_PR_ReducedSmoke_Def.xml`  
  Synthetic reduced field-like geometry for CPU smoke testing of PR pore-pressure
  fields.
- `xCaseSainteMonique_PR_ReducedSmoke_win64_CPU_debug.bat`  
  Debug CPU launcher for the reduced smoke case.
- `CaseSainteMonique_PR_TODO_Def.xml`  
  Historical TODO scaffold kept as a reminder that field reproduction remains
  data- and feature-blocked.
- `analyze_sainte_smoke.py`  
  Small postprocessor for the reduced smoke summary.
- `sainte_smoke_summary.csv`  
  Curated output from the latest reduced smoke; full generated solver outputs
  are not retained.

## Smoke Status

Latest reduced placeholder smoke:

| Item | Result |
| --- | --- |
| GenCase | code=0 |
| DualSPHysics CPU Release | code=0 |
| TimeMax | 0.0002 s |
| Excluded particles | 0 |
| Material particles | 556 |
| Boundary particles | 1173 |
| Max velocity | `1.9849e-3 m/s` |
| Mean velocity | `6.3462e-4 m/s` |
| Max displacement | `2.1000e-7 m` |
| PorePress range | `0` to `3196.09 Pa` |
| ExcessPorePress range | `0` to `8.77 Pa` |
| PorePressRate max | `1.19e5 Pa/s` |
| DivVel range | `-2.80e-4` to `0 1/s` |

The reduced smoke verifies that the current CPU PR implementation can generate
and advance a small field-like geometry while writing the expected pore-pressure
diagnostics.

## Strict Reproduction Reclassification

This reduced placeholder smoke must not be counted as Sainte-Monique
reproduction complete. The validated field case remains blocked by missing
topography, material zoning, sensitive-clay calibration, initial stress and
pore-pressure state, production boundary assumptions, checkpoint/restart
workflow, and GPU-scale runtime.

## Strict Reproduction Gaps

- Missing Sainte-Monique field topography.
- Missing material zoning and sensitive-clay calibration.
- Missing validated initial stress and pore-pressure state.
- Missing production boundary assumptions for the field domain.
- Full-scale runs require GPU implementation and checkpoint/restart workflow.

This case is CPU-smoke runnable in reduced placeholder form only. Under the full
CPU completion gate, it is acceptable as a minimum field-application health
check only if the actual Sainte-Monique field reproduction is explicitly
deferred to the material-model/GPU phase.
