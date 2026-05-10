# Cryer Reduced Smoke Status

Date: 2026-05-10

Case: `CaseCryer_PR_Smoke_Def.xml`

Scope: reduced CPU smoke only, not strict Cryer reproduction.

## Result

- GenCase: `code=0`
- DualSPHysics CPU Debug: `code=0`
- Excluded particles: `0`
- Output frame: `Part_0001` at about `t=0.000501 s`
- Particle count stored at `Part_0000`: `540`

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

The reduced smoke confirms that a Cryer-labeled PR scaffold can run and write the
u-pw fields. It does not validate the Cryer analytical solution or strict drained
spherical/axisymmetric boundary behavior.

## Remaining Strict-Reproduction Blockers

- exact Cryer geometry/radius;
- drained boundary treatment around the specimen;
- analytical center pressure postprocessing;
- useful-resolution GPU run.
