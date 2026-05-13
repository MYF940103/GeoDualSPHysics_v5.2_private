# M3e MCC Feedback-Off Reporting Package

## Objective

M3e is not a new simulation stage. It consolidates the CPU-only Modified Cam
Clay feedback-off platen triaxial results from M3c, M3d, M3d2, and M3d3 into a
reduced reporting package.

The package is stored in:

`examples/u-pw/04_Undrained_Triaxial/experiments/M3e_MCCFeedbackOffPackage/`

## Scope

This package covers:

- CPU-only `SoilConstitutiveModel=3`.
- Explicit top/bottom platen workflow.
- Selected lateral `FlexibleConfiningStress`.
- Pairwise platen reaction diagnostic.
- `PorePressureFeedback=0`.
- `SaveMccState` output and MCC return diagnostics.

This package does not cover:

- Full u-pw pore-pressure feedback.
- GPU MCC.
- true actuator reaction.
- strict drained/undrained MCC paper reproduction.
- new parameter sensitivity.

## Cases Included

The package inventory includes:

1. M3c high-pc MCC smoke.
2. M3c mild-yield MCC smoke.
3. M3d high-pc extended MCC.
4. M3d mild-yield extended MCC.
5. M3d2 half-speed loading diagnostic.
6. M3d2 early-stop diagnostic.
7. M3d2 tight-return diagnostic.
8. M3d3 baseline no-substepping case.
9. M3d3 fixed 4-substep case.
10. M3d3 adaptive 16-substep case.
11. M3d3 adaptive 16-substep partial-fallback case.
12. M3d3 half-speed adaptive diagnostic case.

The main tables are:

- `m3e_case_inventory.csv`
- `m3e_summary_metrics.csv`
- `m3e_return_status_summary.csv`
- `m3e_mcc_state_summary.csv`
- `m3e_reaction_summary.csv`
- `m3e_pore_pressure_summary.csv`
- `m3e_stress_path_summary.csv`

## What Is Validated

The reduced route validates that the GeoDualSPHysics CPU path can parse,
initialize, update, and output MCC state for feedback-off platen triaxial
smokes.

Specific validated pieces:

- `SoilConstitutiveModel=3` parser and state arrays.
- `SaveMccState` fields for `pc`, void ratio, plastic strains, return status,
  residual, iterations, and substepping diagnostics.
- CPU MCC stress update branch in the explicit platen workflow.
- high-pc MCC behaves elastic-like: final yield fraction remains zero in the
  extended case.
- mild MCC yields and evolves `pc`, void ratio, plastic volumetric strain, and
  equivalent plastic strain.
- pairwise reaction and specimen p'-q diagnostics are available.
- feedback-off pore pressure remains bounded in the tested windows.

## What Is Not Clean Yet

The original-rate mild MCC extended case is not a clean validation case. It
still has a local return issue:

```text
M3d/M3d3 baseline final ReturnStatus = -3:8 | 0:2 | 1:397
```

M3d2 showed this is local rather than global: the failed particles are near the
bottom cap/interior transition. Higher iteration limits and tighter tolerance
did not remove the final failed set. Half-speed loading clears the final failed
set but still has transient failure episodes.

M3d3 substepping results:

```text
baseline:             -3:8|0:2|1:397
fixed_substeps4:      -3:18|-1:8|0:2|2:379
adaptive_substeps16:  -3:10|-1:8|0:2|1:387
adaptive_fallback16:  -5:17|0:2|1:387|2:1
half_speed_adaptive:  0:12|1:395
```

The fallback case removes final `-3` by explicitly marking partial fallback
with `-5`. That is a safety diagnostic, not a validation setting.

The mild MCC feedback-off route also produces strong negative mean pore
pressure. Because full pore-pressure feedback remains off, this should be read
as a reduced diagnostic response rather than a strict undrained MCC result.

## Figures

Recommended main figures:

1. `figures/m3e_pq_path_main.*`
2. `figures/m3e_reaction_stress_strain_main.*`
3. `figures/m3e_pc_evolution_main.*`
4. `figures/m3e_void_ratio_evolution_main.*`
5. `figures/m3e_plastic_vol_strain_main.*`
6. `figures/m3e_eq_plastic_strain_main.*`
7. `figures/m3e_return_failure_counts_main.*`
8. `figures/m3e_pore_pressure_main.*`

Recommended supplementary figures:

1. `figures/m3e_line_search_failure_counts_main.*`
2. `figures/m3e_porepressrate_supp.*`
3. `figures/m3e_velocity_supp.*`
4. `figures/m3e_return_iterations_supp.*`
5. `figures/m3e_yield_residual_supp.*`
6. `figures/m3e_substep_count_supp.*`

## Main Conclusion

The MCC CPU feedback-off route is viable as a reduced prototype. It is not yet
clean enough for strict MCC validation at the original loading rate.

High-pc MCC can be used as an elastic-like MCC reference. Mild MCC can be used
to inspect yielding, state evolution, reaction reduction, and p'-q trends, but
must carry the local-return and feedback-off pore-pressure caveats.

## Recommended Next Steps

Route A, recommended for clean validation: M3f return/staging refinement.

- Clean original-rate mild MCC.
- Reduce transient return failures.
- Improve early adaptive substepping or line search.
- Consider smoother platen velocity staging.

Route B, acceptable for documentation/planning only: M4 MCC comparison
planning.

- Design drained/undrained MCC comparison.
- Keep full feedback and GPU deferred.
- Do not present current mild feedback-off pressure as strict undrained
  validation.

If the objective is clean MCC validation, M3f should come before any strict
comparison campaign. If the objective is planning, M4 can proceed as a
paper-design exercise.
