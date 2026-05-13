# M3d MCC Feedback-Off Refinement Report

## Scope

M3d extends the M3c CPU Modified Cam Clay stress-update smoke to the T5c
extended platen window (`TimeMax=0.018 s`). The cases keep
`PorePressureFeedback=0`, use explicit top/bottom platens, retain lateral
`FlexibleConfiningStress`, and save MCC state plus pairwise platen reaction
diagnostics.

No source code was changed in M3d.

## Cases

| Case | Purpose | `pc0` | Feedback | TimeMax |
| --- | --- | ---: | --- | ---: |
| `mcc_high_pc` | elastic-like MCC reference | `100000 Pa` | off | `0.018 s` |
| `mcc_mild_yield` | mild-yield MCC state-evolution check | `120 Pa` | off | `0.018 s` |

Both cases use the M3c MCC CPU stress update branch, the T5/T4t explicit
platen workflow, and pairwise platen reaction diagnostics. The reaction is a
pairwise fluid-bound interaction accumulator, not a full prescribed-motion
actuator reaction.

## Run Status

| Metric | High-pc | Mild-yield |
| --- | ---: | ---: |
| code | `0` | `0` |
| excluded | `0` | `0` |
| DtMin adjustments | `0` | `0` |
| max velocity | `4.70e-3 m/s` | `5.52e-3 m/s` |
| cap leakage diagnostic | `0` | `0` |

The platen motion and lateral confinement remained numerically stable in both
cases. The top platen displacement follows the prescribed velocity window and
the bottom platen remains fixed.

## MCC State Evolution

| Metric | High-pc | Mild-yield |
| --- | ---: | ---: |
| final `MccYieldFlag` fraction | `0.0` | `0.97543` |
| final `MccPc` mean | `100000 Pa` | `119.63 Pa` |
| final `MccVoidRatio` mean | `0.799624` | `0.800493` |
| final `MccPlasticVolStrain` mean | `0` | `-2.75e-4` |
| final `MccEqPlasticStrain` max | `0` | `2.56e-3` |
| final `Kplastic` max | `0` | `2.56e-3` |

The high-pc case stays elastic-like: `pc` is unchanged, plastic strain is zero,
and `MccReturnStatus=0:407`.

The mild-yield case activates plasticity over most of the specimen and evolves
`pc`, void ratio, plastic volumetric strain, and equivalent plastic strain.
However, the extended run exposes local return robustness issues.

## Return Mapping

| Metric | High-pc | Mild-yield |
| --- | ---: | ---: |
| final status counts | `0:407` | `-3:8|0:2|1:397` |
| final max return iterations | `0` | `26` |
| final converged plastic residual max | `0` | `6.42e-5` |
| final raw residual max | `8.11e7` | `4.49e3` |

For the high-pc elastic case, the large raw residual is the elastic yield
margin, not a plastic-return residual.

For the mild case, `397/407` particles converge plastically at the final frame,
but `8/407` particles report `MccReturnStatus=-3` (line-search failure). The
failed particles are explicitly flagged; this is not a silent elastic fallback.
Because local return failure is a no-go criterion, the mild extended case is a
diagnostic partial pass rather than a validation pass.

## Stress Path And Reaction

| Metric | High-pc | Mild-yield |
| --- | ---: | ---: |
| final `p'` proxy | `395.91 Pa` | `47.26 Pa` |
| final `q` proxy | `1091.13 Pa` | `60.58 Pa` |
| final `Fz_proxy` | `3.176 N` | `0.248 N` |
| final pairwise reaction average | `3.338 N` | `0.286 N` |
| pairwise / `Fz_proxy` | `1.051` | `1.155` |
| final force-balance error | `0.0506` | `0.0346` |

The high-pc MCC response is close to the T5c high-strength DP extended
response (`p'≈385.80 Pa`, `q≈1073.74 Pa`). The mild MCC response is
substantially softer than T5c mild DP (`q≈60.6 Pa` vs `120.5 Pa`) and has a
lower pairwise reaction.

## Pore Pressure

| Metric | High-pc | Mild-yield |
| --- | ---: | ---: |
| final mean `PorePress` | `9.56e4 Pa` | `-2.25e5 Pa` |
| final `PorePressRate` maxAbs | `1.37e7 Pa/s` | `6.33e7 Pa/s` |

The pore-pressure response remains bounded in the sense that the run finishes
without excluded particles, `DtMin` bursts, or velocity blow-up. The mild MCC
case develops a much stronger negative mean pore pressure than T5c mild DP.
Because feedback is off, this is still a reduced diagnostic response, not a
strict undrained MCC validation.

## Figures And CSV

The experiment directory contains:

- `m3d_case_summary.csv`
- `m3d_platen_reaction_metrics.csv`
- `m3d_confinement_diagnostics.csv`
- `m3d_axial_stress_strain_metrics.csv`
- `m3d_mcc_state_metrics.csv`
- `m3d_mcc_yield_return_metrics.csv`
- `m3d_stress_path_metrics.csv`
- `m3d_pore_pressure_metrics.csv`
- `m3d_comparison_to_dp_t5c.csv`
- `m3d_stability_metrics.csv`

Figures include reaction stress-strain, `p'-q`, `pc`, void ratio, plastic
volumetric strain, equivalent plastic strain, yield fraction, return
iterations, residuals, pore pressure, `PorePressRate`, `DivVel`, velocity, and
pairwise reaction. Lateral confinement diagnostics are also retained; the
selected lateral target count remains `112` in the startup diagnostics and the
cap axial acceleration diagnostic remains zero for the selected lateral
confinement route.

## Conclusions

1. The high-pc MCC extended case remains elastic-like and stable.
2. The mild MCC extended case is globally stable at the solver level, but it
   does not fully pass the MCC local-return gate because a small set of
   particles reports `MccReturnStatus=-3`.
3. MCC state output works and is useful for diagnosing `pc`, void ratio,
   plastic volumetric strain, equivalent plastic strain, return status, and
   residuals.
4. Pairwise reaction remains bounded and usable as a reduced diagnostic, with
   the known caveat that it is not the full prescribed-motion actuator
   reaction.
5. M3d should not be promoted directly to a clean M3e validation package until
   the mild-yield return robustness issue is addressed or explicitly scoped as
   a limitation.

## Recommended Next Step

Do not proceed directly to MCC paper-validation or full feedback. The next
step should be a narrow M3d-return robustness pass:

- inspect particles with `MccReturnStatus=-3`;
- add diagnostics by region / stress state;
- evaluate whether substepping, tighter line search, or safer local fallback is
  needed;
- keep the test feedback-off and CPU-only.

After that, M3e measurement/reporting consolidation can proceed if the local
return failure is removed or bounded by an explicitly justified diagnostic
policy.

Full pore-pressure feedback and GPU remain deferred.
