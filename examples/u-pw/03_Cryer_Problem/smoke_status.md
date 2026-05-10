# Cryer-Like Strict/Minimal CPU Smoke Status

Date: 2026-05-11

Case: `CaseCryer_PR_Smoke_Def.xml`

Scope: Cryer-like CPU smoke. This is stronger than a TODO scaffold because it
runs the u-pw PR path, writes pore-pressure fields, and produces a near-center
pore-pressure history. It is still not strict analytical Cryer reproduction.

## Result

- GenCase: `code=0`
- DualSPHysics CPU Release: `code=0`
- Excluded particles: `0`
- Output frame: `Part_0001` at about `t=0.000501 s`
- Particle count stored at `Part_0000`: `540`
- NaN/Inf scan in `PartCsv_*.csv`: not detected
- Near-center pressure analysis: `analyze_cryer_smoke.py`

## Output Fields Checked

The CSV output contained:

- `PorePress`
- `ExcessPorePress`
- `PorePressRate`
- `DivVel`
- `LapPorePress`
- `LapZ`
- `PorePressureAccelDiff`

## Interpretation

The Cryer-like smoke confirms that a Cryer-labeled PR scaffold can run, write
the u-pw fields, and produce a bounded near-center pore-pressure proxy.

Latest analysis summary:

- frames: `2`
- center pore pressure at final frame: `7930.27 Pa`
- center excess pressure at final frame: `327.52 Pa`
- final pore-pressure range: `[0, 10296.6] Pa`
- final excess-pressure range: `[0, 536.38] Pa`

This does not validate the Cryer analytical solution or strict drained
spherical/axisymmetric boundary behavior.

## Remaining Strict-Reproduction Blockers

- exact Cryer geometry/radius;
- drained boundary treatment around the specimen;
- analytical center pressure postprocessing;
- useful-resolution GPU run.
