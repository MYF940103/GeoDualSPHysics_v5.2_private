# T4p Interpretation Of CapConfiningStress Failure

## What T4o Showed

T4o tested whether retaining cap support after all-surface isotropic
confinement would preserve the hydrostatic state. It did not.

Key results:

- Stage A all-surface: `p' approx 46.38 Pa`, `q approx 15.65 Pa`;
- T4n2 lateral-only restart: `q approx 37.89 Pa`;
- T4o lateral+cap restart: `p' approx 23.87 Pa`, `q approx 61.92 Pa`;
- delayed feedback remained unstable with max `PorePressRate approx
  9.32e11 Pa/s`.

## Correct Interpretation

The failure should not be treated as a scalar cap-force tuning problem.
`CapConfiningStress` is a diagnostic acceleration patch:

- it acts directly on material cap particles;
- it distributes `p0*pi*R^2` over selected cap mass;
- it skips edge-ring particles;
- it has no contact/platen kinematics;
- it does not create a reaction boundary;
- it does not separate platen particles from soil material.

The T4o result shows that this mechanism is not compatible with the
all-surface Zhao confinement equilibrium. It can be symmetric and still produce
a stronger deviatoric mismatch than the lateral-only restart.

## Production Status

`CapConfiningStress` should be retained only as a diagnostic tool. It should
not be recommended as a production triaxial cap/platen boundary.

Do not continue tuning:

- `CapConfiningStressP0`;
- cap ramp times;
- cap target mk values;
- cap force scaling;
- cap support as a validation boundary.

## Route Change

The next route should model top/bottom platens explicitly:

- bottom fixed platen;
- top prescribed-velocity/displacement platen;
- lateral flexible confinement;
- specimen/platen measurement separation;
- axial reaction output.

This is closer to Zhao's triaxial setup and to laboratory triaxial mechanics.

## Current Validation Status

Axial loading, DP, MCC, and GPU parity remain deferred until the platen support
stage is stable under the elastic u-pw framework.
