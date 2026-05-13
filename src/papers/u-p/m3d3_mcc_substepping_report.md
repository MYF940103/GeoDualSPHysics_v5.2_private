# M3d3 MCC Constitutive Substepping Report

## Objective

M3d3 adds opt-in CPU-only robustness controls for the Modified Cam Clay local
return mapping used by `SoilConstitutiveModel=3`. The target was the local
`MccReturnStatus=-3` line-search failure observed in the M3d/M3d2 mild MCC
feedback-off platen triaxial smoke.

The changes do not alter the PR pore-pressure equation, FlexibleConfiningStress,
elastic, DP, or DP-softening behavior. Full pore-pressure feedback remains off.
GPU still hard-errors for `SoilConstitutiveModel=3`.

## Source Changes

Implemented new MCC XML parameters in `StSoilCte` and parser/logging:

- `MccSubstepping`: `0/1`, default `0`.
- `MccMaxSubsteps`: default `1`, capped in parser.
- `MccSubstepMode`: `0` fixed, `1` adaptive on failed return, `2` adaptive by
  trial increment proxy.
- `MccSubstepStrainThreshold`: used only by mode `2`.
- `MccAdmissibilityGuard`: `0/1`, default `0`.
- `MccFailureFallback`: `0` fail status only, `1` retry only, `2` keep last
  converged substep and mark partial fallback.

Implemented MCC-only CPU local substepping around the existing M3c return
mapping:

1. Build a compression-positive old stress and full elastic trial stress.
2. Split the stress increment into local subtrials.
3. Run the existing MCC return mapping per substep.
4. Update stress, `pc`, void ratio, plastic volumetric strain, equivalent
   plastic strain, plastic multiplier, and residual continuously across
   successful substeps.
5. On failure, retry with more substeps for adaptive mode.
6. With fallback mode `2`, keep the last converged substep and set explicit
   status `-5`. This is not silent elastic fallback.

Implemented admissibility checks for finite stress/state, `p'` above
`MccTensionCutoff`, positive finite `pc`, finite void ratio above `-0.999`,
and non-negative finite plastic multiplier. Guard failures are counted and can
trigger substep retry.

Added `SaveMccState` output fields:

- `MccSubstepCount`
- `MccSubstepFailureCount`
- `MccAdmissibilityFailureCount`
- `MccFallbackUsed`

## Return Status

M3d3 keeps the M3c meanings and adds:

- `2`: plastic return converged using substepping.
- `-5`: partial substep fallback used, last converged substep kept explicitly.
- `-6`: admissibility guard failure.

Negative status values remain failure/guard diagnostics and must not be read as
clean validation.

## Cases

All cases use the M3d mild MCC feedback-off explicit-platen workflow:

- `PorePressureFeedback=0`
- `SoilConstitutiveModel=3`
- `MccInitialPreconsolidationPressure=120 Pa`
- selected lateral FlexibleConfiningStress
- top prescribed platen velocity
- bottom fixed platen
- pairwise platen reaction diagnostics

Cases run:

| Case | Substepping setup | Time window |
| --- | --- | --- |
| baseline | off | `0.018 s`, `vz=-0.005 m/s` |
| fixed_substeps4 | fixed 4 substeps, guard on | `0.018 s`, `vz=-0.005 m/s` |
| adaptive_substeps16 | adaptive retry to 16, guard on | `0.018 s`, `vz=-0.005 m/s` |
| adaptive_fallback16 | adaptive retry to 16, guard on, partial fallback on | `0.018 s`, `vz=-0.005 m/s` |
| half_speed_adaptive | adaptive retry to 16, guard on | `0.036 s`, `vz=-0.0025 m/s` |

## Solver Status

All M3d3 CPU Release cases finished:

```text
code=0
excluded=0
DtMin adjustments=0
```

CPU Release and GPU Release builds passed after the source patch. No GPU
simulation was run.

## Return Robustness Results

Final return-status counts:

| Case | Final `MccReturnStatus` | Final negative count | Final `-3` count |
| --- | --- | ---: | ---: |
| baseline | `-3:8|0:2|1:397` | 8 | 8 |
| fixed_substeps4 | `-3:18|-1:8|0:2|2:379` | 26 | 18 |
| adaptive_substeps16 | `-3:10|-1:8|0:2|1:387` | 18 | 10 |
| adaptive_fallback16 | `-5:17|0:2|1:387|2:1` | 17 | 0 |
| half_speed_adaptive | `0:12|1:395` | 0 | 0 |

The original-rate fixed and adaptive substepping cases did not cleanly solve
the local return problem. They reduced or moved some line-search failures but
introduced tension-cutoff status on edge/top-bottom surface particles. This
means local constitutive substepping alone is not a complete cure for the
original loading rate.

Adaptive fallback removes final `-3` by keeping the last converged local
substep, but it leaves explicit `-5` partial-fallback particles. This is useful
as a safety diagnostic, not as a clean validation setting.

The half-speed adaptive case is the only clean final-frame route in M3d3:

```text
final ReturnStatus = 0:12 | 1:395
final -3 count = 0
final negative status count = 0
```

It still had intermediate local failure episodes, so it is a cleaner reduced
route rather than a strict proof of global return robustness.

## State Smoothness

Final mild MCC state summaries:

| Case | `pc_mean` Pa | `e_mean` | `PlasticVolStrain_mean` |
| --- | ---: | ---: | ---: |
| baseline | 119.630 | 0.800493 | -2.750e-4 |
| fixed_substeps4 | 119.175 | 0.801116 | -6.175e-4 |
| adaptive_substeps16 | 119.634 | 0.800494 | -2.723e-4 |
| adaptive_fallback16 | 119.424 | 0.800784 | -4.331e-4 |
| half_speed_adaptive | 119.532 | 0.800631 | -3.481e-4 |

The half-speed adaptive case keeps smooth `pc`, void-ratio, and plastic-strain
evolution. Fixed substepping changes the plastic volumetric strain more strongly
and is not recommended as the default diagnostic route.

## Residuals And Response

Final converged plastic residuals remain small:

- baseline: `6.42e-5`
- adaptive_substeps16: `7.17e-5`
- adaptive_fallback16: `1.27e-4`
- half_speed_adaptive: `9.29e-5`

Raw residual maxima remain large whenever failed or partial-fallback particles
exist. They should not be mixed with the converged residual metric.

Pairwise reaction and p'-q response remain bounded. Final pairwise reaction
averages are approximately:

- baseline: `0.286 N`
- fixed_substeps4: `0.284 N`
- adaptive_substeps16: `0.285 N`
- adaptive_fallback16: `0.284 N`
- half_speed_adaptive: `0.255 N`

Mean pore pressure remains bounded but negative in all mild MCC cases. The
half-speed adaptive case ends at about `-2.82e5 Pa`, so this remains a
feedback-off reduced diagnostic path, not strict undrained MCC validation.

## Interpretation

M3d3 confirms that the remaining MCC return issue is coupled to local loading
increment and boundary/platen-zone stress path. The cleanest result comes from
reducing the global platen velocity, not from fixed substepping alone.

Recommended route:

- keep the substepping/admissibility infrastructure because it gives useful
  opt-in diagnostics and safe retry/fallback behavior;
- do not use fixed substepping as a validation setting for the original-rate
  mild case;
- use half-speed adaptive as the clean reduced MCC feedback-off diagnostic
  route if M3e reporting consolidation proceeds;
- keep adaptive fallback as a safety/debug option only because it emits `-5`
  partial-fallback status.

## Next Step

M3e can proceed only as a reduced feedback-off MCC reporting package that
clearly distinguishes:

- clean half-speed adaptive final response;
- original-rate partial/failure diagnostics;
- no full pore-pressure feedback;
- no strict paper reproduction;
- no GPU MCC.

If the goal is original-rate clean MCC validation with zero intermediate return
failures, then another source-level step is still needed, likely combining
better boundary/platen staging, strain-rate control, or a more robust local
return/substep acceptance rule.

Full feedback and GPU remain deferred.
