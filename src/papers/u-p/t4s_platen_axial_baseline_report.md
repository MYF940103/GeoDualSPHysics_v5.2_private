# T4s Platen Axial Baseline Report

## Purpose

T4s establishes a reduced feedback-off platen-based axial triaxial baseline.
It is not a full paper reproduction and it is not a DP/MCC validation. The
goal is to keep the explicit platen route from T4q/T4r, retain clean
specimen-only measurements, and run a slightly longer elastic axial-compression
window with and without lateral flexible confinement.

No source code was modified. The stage is CPU-only, linear elastic, and
`PorePressureFeedback=0`.

## Experiment Directory

`examples/u-pw/04_Undrained_Triaxial/experiments/T4s_PlatenAxialBaseline/`

Main files:

- `CaseT4s_PlatenAxial_NoConfinement_Def.xml`
- `CaseT4s_PlatenAxial_LateralConfinement_Def.xml`
- `make_t4s_cases.py`
- `analyze_t4s_platen_axial_baseline.py`
- `t4s_case_summary.csv`
- `t4s_platen_motion_metrics.csv`
- `t4s_specimen_stress_proxy.csv`
- `t4s_pore_pressure_strain_metrics.csv`
- `t4s_measurement_region_metrics.csv`
- `t4s_confinement_metrics.csv`
- `t4s_reaction_proxy_metrics.csv`
- `figures/`

## Case Setup

Both T4s cases use the explicit platen geometry introduced in T4q:

- specimen: `mkfluid=0`, `407` particles;
- top platen: moving `mkbound=1`, `74` particles;
- bottom platen: fixed `mkbound=2`, `74` particles;
- top prescribed velocity: `v_z=-0.005 m/s`;
- bottom prescribed displacement: fixed at zero;
- `SoilConstitutiveModel=0`;
- `HydraulicElevationSource=0`;
- `PorePressureFeedback=0`;
- `TimeMax=0.006 s`;
- `TimeOut=0.0005 s`.

The two retained CPU Release cases are:

| Case | Lateral confinement | Feedback |
| --- | --- | --- |
| Platen axial, no confinement | off | off |
| Platen axial, lateral confinement | selected `FlexibleConfiningStress` | off |

The lateral-confinement case uses the T3/T4 selected route:

- `FlexibleConfiningStress=1`;
- `ConfiningStressUseFiSelector=1`;
- `ConfiningStressUseLateralSelector=1`;
- `ConfiningStressP0=50 Pa`;
- `CapConfiningStress=0`.

## CPU Runs

Both CPU Release baselines completed cleanly:

| Case | Code | Excluded | DtMin adjustments | `Kplastic` max |
| --- | ---: | ---: | ---: | ---: |
| Platen axial, no confinement | `0` | `0` | `0` | `0` |
| Platen axial, lateral confinement | `0` | `0` | `0` | `0` |

The generated CSV files contain no `NaN` or `Inf` values.

## Platen Motion

The prescribed platen kinematics remain correct over the longer T4s window:

| Case | Final top displacement | Final top `v_z` mean | Bottom displacement |
| --- | ---: | ---: | ---: |
| No confinement | `-3.00e-5 m` | `-3.39e-3 m/s` | `0` |
| Lateral confinement | `-3.00e-5 m` | `-3.39e-3 m/s` | `0` |

The final displacement matches the prescribed `-0.005 m/s` motion over about
`0.006 s`. The saved velocity field is a post-integration/output-frame value,
so the displacement is the more reliable prescribed-motion check.

## Specimen And Measurement Separation

The specimen/platen grouping remains clean:

- final total particles: `555`;
- final specimen particles: `407`;
- final top platen particles: `74`;
- final bottom platen particles: `74`;
- center-core measurement particles: `15`;
- platen contamination in center-core, medium, and specimen-minus-edge
  regions: `0`.

This keeps the T4s stress and pore-pressure curves cleaner than the earlier
AccInput material-layer route.

## Stress And Reaction Proxy

T4s still uses the T4r specimen-stress proxy because true platen reaction is
not exposed for ordinary fixed/moving `mkbound` platens:

```text
sigma_a_proxy = -mean(Sigma_zz) over specimen particles
Fz_proxy = sigma_a_proxy * pi * R^2
```

Final specimen-wide proxy values:

| Case | `p'` proxy | `q` proxy | `sigma_a_proxy` | `Fz_proxy` |
| --- | ---: | ---: | ---: | ---: |
| No confinement | `117.91 Pa` | `346.17 Pa` | `348.69 Pa` | `0.9859 N` |
| Lateral confinement | `145.66 Pa` | `332.47 Pa` | `367.31 Pa` | `1.0385 N` |

The lateral-confinement case keeps a higher mean stress proxy and slightly
lower `q` proxy than the no-confinement case. The center-core and
specimen-minus-edge regions show the same trend, while remaining free of
platen contamination.

Final center-core values:

| Case | `p'` proxy | `q` proxy | Mean pore pressure | `Fz_proxy` |
| --- | ---: | ---: | ---: | ---: |
| No confinement | `152.62 Pa` | `469.62 Pa` | `5.31e4 Pa` | `1.3167 N` |
| Lateral confinement | `185.68 Pa` | `448.25 Pa` | `6.53e4 Pa` | `1.3699 N` |

The proxy is useful for a reduced baseline trend, not for strict axial reaction
validation.

## Pore Pressure And Stability

With feedback disabled, the PR pore-pressure response remains bounded over
the retained short-to-medium window:

| Case | Final specimen mean `PorePress` | Final `PorePressRate` maxAbs | Final `DivVel` maxAbs | Final velocity max |
| --- | ---: | ---: | ---: | ---: |
| No confinement | `3.50e4 Pa` | `2.06e7 Pa/s` | `3.10e-2 1/s` | `5.47e-3 m/s` |
| Lateral confinement | `4.54e4 Pa` | `2.04e7 Pa/s` | `3.07e-2 1/s` | `5.53e-3 m/s` |

These are not validation targets. They show that the feedback-off u-pw PR
fields remain finite and postprocessable during explicit platen compression.

## Lateral Confinement

The lateral-confinement case keeps the expected selector diagnostics:

- active lateral targets: `112`;
- legacy material candidates: `407`;
- total absolute confinement force: about `0.4426 N`;
- max confining acceleration: about `1.93 m/s2`;
- lateral inward radial acceleration mean: about `1.87 m/s2`;
- cap axial leakage diagnostic: `0`.

Thus the moving-platen route and selected lateral `FlexibleConfiningStress`
can coexist over the T4s baseline window.

## True Reaction Patch Decision

No true reaction source patch was implemented in T4s.

The current proxy curves are usable enough for a reduced feedback-off elastic
baseline and for comparing no-confinement versus lateral-confinement platen
workflows. Strict validation eventually needs a true reaction diagnostic, but
it does not need to block the next reduced feedback-off DP smoke if the scope
is clearly labeled.

## Required Answers

1. T4s CPU cases: both completed with `code=0`, `excluded=0`.
2. DtMin/Kplastic: both have `DtMin=0` and `Kplastic=0`.
3. Top prescribed velocity: correct by displacement; final top displacement
   is `-3.00e-5 m`.
4. Bottom fixed platen: correct; bottom displacement remains `0`.
5. Lateral confinement: stable and compatible with explicit platens.
6. Pore pressure response: bounded over the feedback-off T4s window.
7. `p'-q` proxy: cleaner than pre-platen routes because platens are excluded;
   still a proxy, not strict stress-path validation.
8. `Fz_proxy`: usable as a specimen-stress proxy, not true platen reaction.
9. Immediate true reaction patch: not required for the reduced T4s baseline,
   but still required before strict validation.
10. Next reduced route: T5 DP feedback-off baseline can be considered, with
    clear caveats.
11. Full feedback, MCC, and GPU remain deferred.
