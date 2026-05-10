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
- `CaseRetrogressiveSlope_PR_TODO_Def.xml`  
  Historical placeholder kept to document the original feature-blocked state.

## Smoke Status

Latest reduced smoke:

| Item | Result |
| --- | --- |
| GenCase | code=0 |
| DualSPHysics CPU Debug | code=0 |
| TimeMax | 0.0002 s |
| Excluded particles | 0 |
| Material particles | 602 |
| Boundary particles | 1173 |
| Max velocity | `1.98e-3 m/s` |
| Mean velocity | `1.97e-3 m/s` |
| PorePress range | `399.02` to `2561.64 Pa` |
| ExcessPorePress range | `5.64` to `12.09 Pa` |
| PorePressRate max | `1.66e5 Pa/s` |
| DivVel range | `-4.41e-4` to `-3.31e-5 1/s` |

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
