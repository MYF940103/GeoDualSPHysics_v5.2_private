# 04 Undrained Triaxial

This directory tracks the u-pw PR reproduction path for the paper's undrained
triaxial tests.

The current runnable case is a reduced CPU smoke test, not a strict triaxial
reproduction. It uses the current Drucker-Prager soil path, a small 2D column,
and native DualSPHysics `accinput` on the top `mkfluid=1` material layer to
apply a tiny axial loading increment.

## Files

- `CaseUndrainedTriaxial_PR_Smoke_Def.xml`  
  Reduced CPU smoke case with u-pw PR enabled, undrained top drainage delayed,
  pressure feedback set to excess/difference-gradient mode, Shepard smoothing,
  and Supporting Information style damping.
- `xCaseUndrainedTriaxial_PR_Smoke_win64_CPU_debug.bat`  
  Debug CPU launcher for the smoke case.
- `TriaxialAxialAcc_m1.csv`  
  Native AccInput history for the top material layer. The final axial
  acceleration is only `-0.047619 m/s2`.
- `analyze_triaxial_smoke.py`  
  Lightweight postprocessing scaffold for approximate `p'` and `q` estimates
  from `Sigma_kk` / `Sigma_ij` fields.
- `CaseUndrainedTriaxial_PR_TODO_Def.xml`  
  Historical TODO scaffold retained as a reminder that strict reproduction is
  not complete.

## Smoke Status

Latest short smoke:

| Item | Result |
| --- | --- |
| GenCase | code=0 |
| DualSPHysics CPU Debug | code=0 |
| TimeMax | 0.001 s |
| Excluded particles | 0 |
| Fluid/material particles | 1000 |
| AccInput target layer | `mkfluid=1`, 10 particles |
| Max velocity | `1.86e-5 m/s` |
| Mean velocity | `2.47e-6 m/s` |
| ExcessPorePress range | `0.0903` to `15.48 Pa` |
| PorePressRate max | `3.74e4 Pa/s` |
| DivVel range | `-3.15e-4` to `-4.01e-8 1/s` |
| PorePressureAccelDiff.z range | `-2.21e-2` to `1.67e-6 m/s2` |

The smoke test confirms code execution, pore-pressure fields, feedback
diagnostics, damping, and native AccInput loading are wired correctly. The pore
pressure response is small and positive under the tiny compressive increment.

## Strict Reproduction Gaps

- No calibrated Modified Cam Clay model is used. The current DP model can only
  support qualitative smoke tests unless calibrated against the paper setup.
- The case does not yet implement true triaxial stress control.
- Lateral confinement is represented only by fixed side boundaries, not by a
  prescribed confining stress boundary.
- Stress-path output is postprocessed approximately from existing stress
  components; a strict `p'`-`q` workflow still needs validation.
- This case is not a long CPU parameter-tuning target. Longer and higher
  resolution reproduction should wait until the GPU path is available.
