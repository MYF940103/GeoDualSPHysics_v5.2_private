# 05 Retrogressive Slope

This directory tracks the u-pw PR reproduction path for the paper's
retrogressive slope / landslide benchmark.

The current runnable case is a reduced CPU smoke test. It is deliberately small
and qualitative: a narrow 3D soil wedge with gravity, current Drucker-Prager
soil, hydrostatic pore pressure, and PR pore-pressure diagnostics. It is not a
validated retrogression or landslide reproduction.

## Files

- `CaseRetrogressiveSlope_PR_ReducedSmoke_Def.xml`  
  Reduced 3D wedge smoke case. Feedback is off in this first smoke so the case
  verifies geometry, gravity, stress evolution, PR pressure fields, and output
  health without attempting production landslide coupling.
- `xCaseRetrogressiveSlope_PR_ReducedSmoke_win64_CPU_debug.bat`  
  Debug CPU launcher for the reduced smoke case.
- `analyze_slope_smoke.py`  
  Lightweight summary of displacement, velocity, pore pressure, excess pore
  pressure, and `Kplastic` ranges.
- `slope_smoke_summary.csv`  
  Latest reduced smoke postprocessing summary.
- `CaseRetrogressiveSlope_PR_TODO_Def.xml`  
  Historical placeholder kept to document the original feature-blocked state.

## Smoke Status

Latest reduced smoke:

| Item | Result |
| --- | --- |
| GenCase | code=0 |
| DualSPHysics CPU Release | code=0 |
| TimeMax | 0.0002 s |
| Excluded particles | 0 |
| Particle rows in CSV | 1775 |
| NaN/Inf scan | not detected |
| Max displacement | `2.10e-7 m` |
| Max velocity | `1.98e-3 m/s` |
| Mean velocity | `6.67e-4 m/s` |
| PorePress range | `0` to `2561.64 Pa` |
| ExcessPorePress range | `0` to `12.09 Pa` |
| Kplastic range | `0` to `0` |

The smoke confirms that a reduced slope geometry can run with current CPU PR
fields and write the expected pore-pressure diagnostics.

## Strict Reproduction Reclassification

This reduced wedge smoke must not be counted as strict retrogressive landslide
reproduction complete. It does not include sensitive clay / strain softening,
remolding or destructuration, a validated initial effective-stress and
pore-pressure state, production non-horizontal hydraulic boundaries, or
large-deformation validation. It is a reduced execution check only.

## Strict Reproduction Gaps

- The paper-scale retrogressive mechanism requires sensitive clay /
  strain-softening or remolding behavior. The current DP model is only a
  qualitative placeholder.
- Initial effective stress and pore-pressure construction for a slope is not
  yet validated.
- Production pore-pressure boundary treatment for non-horizontal boundaries is
  still unresolved.
- Feedback is disabled in this reduced smoke; a coupled slope smoke should only
  be attempted after smaller coupled cases and GPU porting are stable.
- Meaningful run sizes require GPU implementation.

This case now satisfies a runnable reduced smoke scaffold, but strict landslide
reproduction remains feature- and GPU-blocked. Under the full CPU completion
gate, this must be recorded as incomplete strict reproduction unless the
sensitive-clay and field-scale requirements are explicitly deferred.
