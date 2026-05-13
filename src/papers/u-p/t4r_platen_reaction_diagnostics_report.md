# T4r Platen Reaction Diagnostics Report

## Purpose

T4r extends the T4q XML-only platen workflow with specimen-only stress-path
postprocessing and a clearly labeled axial reaction proxy.

No source code was modified. This stage is CPU-only, elastic, feedback-off,
and diagnostic. It does not implement DP, MCC, full feedback, GPU support, or
full paper reproduction.

## Experiment Directory

`examples/u-pw/04_Undrained_Triaxial/experiments/T4r_PlatenReactionDiagnostics/`

Main files:

- `CaseT4r_PlatenAxial_NoConfinement_Def.xml`
- `CaseT4r_PlatenAxial_LateralConfinement_Def.xml`
- `make_t4r_cases.py`
- `analyze_t4r_platen_reaction.py`
- `t4r_case_summary.csv`
- `t4r_platen_motion_metrics.csv`
- `t4r_reaction_metrics.csv`
- `t4r_specimen_stress_path_proxy.csv`
- `t4r_measurement_region_metrics.csv`
- `t4r_confinement_diagnostics.csv`
- `figures/`

## Source Audit Result

True platen reaction is not available from the current XML-only workflow.

The existing `SaveFtAce`/floating-force route sums forces for floating bodies
(`FtObjs`). The T4q/T4r platens are ordinary fixed/moving `mkbound` groups:

- top platen: moving `mkbound=1`;
- bottom platen: fixed `mkbound=2`;
- specimen: `mkfluid=0`.

Those groups do not have a per-`mkbound` reaction accumulator in the current
saved outputs. Therefore T4r records:

- `true_reaction_available = 0`;
- `reaction_type = specimen_stress_proxy`.

The proxy is:

```text
sigma_a_proxy = -mean(Sigma_zz) over specimen particles
Fz_proxy = sigma_a_proxy * pi * R^2
```

This is useful for a stable axial-stress signal, but it is not a top-platen
reaction.

## CPU Runs

Both CPU Release cases completed:

| Case | Code | Excluded | DtMin | Kplastic max |
| --- | ---: | ---: | ---: | ---: |
| Platen axial, no confinement | `0` | `0` | `0` | `0` |
| Platen axial, lateral confinement | `0` | `0` | `0` | `0` |

## Platen Motion

The prescribed top-platen motion is reproduced:

| Case | Final top displacement | Final top `v_z` mean | Bottom displacement |
| --- | ---: | ---: | ---: |
| No confinement | `-7.50e-6 m` | `-4.60e-3 m/s` | `0` |
| Lateral confinement | `-7.50e-6 m` | `-4.60e-3 m/s` | `0` |

The final velocity is slightly below the nominal `-0.005 m/s` in saved output
because the final frame is taken after the solver's time integration and output
timing, but the displacement matches the prescribed motion.

## Specimen / Platen Separation

Grouping remains clean:

- specimen: `407` particles;
- top platen: `74` particles;
- bottom platen: `74` particles;
- center measurement core: `15` specimen particles;
- platen contamination in the center measurement core: `0`.

This is a major improvement over the earlier `AccInput` top-material-layer
smoke route, where the loading layer was not a clean platen boundary.

## Stress And Reaction Proxy

Final specimen-wide proxy values:

| Case | `p'` proxy | `q` proxy | `sigma_a_proxy` | `Fz_proxy` |
| --- | ---: | ---: | ---: | ---: |
| No confinement | `27.94 Pa` | `43.47 Pa` | `56.92 Pa` | `0.1609 N` |
| Lateral confinement | `49.10 Pa` | `33.28 Pa` | `71.28 Pa` | `0.2015 N` |

The lateral confinement case has a higher mean effective stress proxy and a
lower deviatoric stress proxy at the final frame. This is consistent with the
lateral confinement providing a more triaxial-like stress state than pure top
platen motion.

The result is still a proxy:

- no true top/bottom reaction force is available;
- no validated axial stress from platen reaction exists;
- no full-feedback coupling is enabled;
- no DP/MCC plasticity is tested.

## Pore Pressure And Stability

With feedback disabled, pore-pressure diagnostics remain bounded in both
cases:

| Case | Final mean `PorePress` | MaxAbs `PorePressRate` | MaxAbs `DivVel` |
| --- | ---: | ---: | ---: |
| No confinement | `4.19e3 Pa` | `3.04e7 Pa/s` | `4.56e-2 1/s` |
| Lateral confinement | `1.25e4 Pa` | `4.02e7 Pa/s` | `6.03e-2 1/s` |

These values are not validation targets. They show that PR diagnostic fields
are active and that the feedback-off platen workflow remains numerically
stable over the short run.

## Lateral Confinement Compatibility

The lateral confinement case retains the healthy T4q selector diagnostics:

- active lateral targets: `112`;
- legacy material candidates: `407`;
- `f_i <= 0.70`: `208`;
- lateral inward radial acceleration mean: about `1.87 m/s2`;
- cap axial leakage diagnostic: `0`;
- symmetry residual remains small.

Thus lateral `FlexibleConfiningStress` and moving explicit platens can coexist
in this reduced CPU workflow.

## Source Patch Decision

No source patch was implemented in T4r.

A future strict reaction patch should be opt-in, CPU-only, and diagnostic-only:

- identify top/bottom platen `mkbound`;
- accumulate specimen-platen interaction force by `mkbound`;
- output true top/bottom `Fz` and `Fz/A0`;
- keep prescribed motion and physics unchanged;
- hard-error on GPU until implemented.

## Required Answers

1. Reliable platen reaction output: no, not from current XML-only fields.
2. Current reaction quantity: specimen-stress proxy, not true reaction.
3. Top prescribed velocity: correct; displacement reaches `-7.50e-6 m`.
4. Bottom fixed platen: correct; displacement remains `0`.
5. Specimen/platen/measurement separation: clean, with `0` platen
   contamination in the center core.
6. Specimen-only `p'-q`: available as a clearer proxy than T4 because platen
   particles are excluded, but still not strict validation.
7. Lateral confinement + platen workflow: stable in the CPU short run.
8. Next step: T4s can proceed as a feedback-off platen-based axial baseline
   using specimen-only proxies, while true reaction remains a source-diagnostic
   blocker for strict validation.
9. Full feedback, DP, MCC, and GPU remain deferred.

