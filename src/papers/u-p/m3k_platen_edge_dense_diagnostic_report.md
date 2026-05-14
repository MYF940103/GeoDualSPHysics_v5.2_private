# M3k Platen/Edge Dense Diagnostic Report

## Objective

M3k is a very-short dense-output diagnostic for the MCC return failures seen in
M3d2/M3f/M3j-B.  No source was modified, full pore-pressure feedback stayed
off, and no GPU simulation was run.

The goal is to inspect the first failure onset with enough temporal resolution
to decide whether the remaining MCC return failures are more consistent with a
boundary/platen/edge local strain-path problem than with a global MCC return
mapping failure.

## Case

Experiment directory:

`examples/u-pw/04_Undrained_Triaxial/experiments/M3k_PlatenEdgeDenseDiagnostic/`

The dense diagnostic case is:

- `CaseM3k_MCCMildDenseOnset_Def.xml`
- `SoilConstitutiveModel=3`
- mild MCC parameters from the previous failed-return baseline
- `PorePressureFeedback=0`
- explicit top platen prescribed velocity
- bottom platen fixed
- selected lateral `FlexibleConfiningStress`
- `SaveMccState=1`
- `SavePlatenReactionDiagnostics=1`
- `TimeMax=0.0025 s`
- `TimeOut=0.0001 s`

The CPU Release run completed:

```text
code=0
excluded=0
DtMin adjustments=0
saved frames=22
saved specimen particles per frame=407
```

## Outputs

The postprocessor `analyze_m3k_platen_edge_dense_diagnostic.py` extracts
geometry, local support, velocity-gradient proxies, stress invariants, MCC
state, and return status from dense `PartCsv` output.

Key CSV outputs:

- `m3k_failure_onset_summary.csv`
- `m3k_failed_particle_timeline.csv`
- `m3k_failed_vs_nonfailed_local_metrics.csv`
- `m3k_neighbor_support_metrics.csv`
- `m3k_velocity_gradient_proxy.csv`
- `m3k_region_failure_statistics.csv`

Key figures:

- `m3k_failed_particle_maps.svg/png`
- `m3k_failed_vs_nonfailed_q_over_p.svg/png`
- `m3k_failed_vs_nonfailed_p_eff.svg/png`
- `m3k_failed_vs_nonfailed_gradv.svg/png`
- `m3k_failed_vs_nonfailed_support.svg/png`
- `m3k_region_failure_count_vs_time.svg/png`
- `m3k_reaction_near_onset.svg/png`

The neighbor/support calculation is a postprocessing proxy from saved particle
positions, not the solver's cell-linked-list neighbor count.

## Failure Onset

The first saved-frame failure occurs at:

```text
t = 0.001005 s
failed particles = 96
ReturnStatus=-1: 92
ReturnStatus=-3: 4
```

The dense output therefore captures the onset before the later broader
negative-status episodes.

The full negative-status timeline remains solver-stable: failures appear in
saved diagnostics, but the run still finishes with `code=0`, `excluded=0`, and
`DtMin=0`.

## Boundary Localization

Failures remain boundary-concentrated.  During the onset window, failed records
are concentrated in edge/cap/lateral regions:

```text
edge_ring:        dominant failed region
lateral_surface:  participates, mostly ReturnStatus=-1
bottom_cap_zone: participates, mostly ReturnStatus=-1
top_cap_zone:    appears in later ReturnStatus=-3 frames
measurement_core: rare; not the main trigger
```

The hardest line-search failures, `ReturnStatus=-3`, are especially localized:

- first onset `-3`: four symmetric particles at the top edge/corner,
  `r/R ~= 0.943`, `z/H ~= 1.0`;
- later `-3`: top cap, lateral, and edge-ring particles dominate;
- a few interior `-3` records appear later, but they are not representative of
  the first onset.

This refines the M3j-B interpretation: bottom fixed-platen adjacency is a
recurring issue in the broader audit, but in this dense onset case the earliest
hard `-3` event is top edge/corner.  The common feature is the mixed cap/platen
and lateral/free-surface boundary environment.

## Support / Neighbor Proxy

The first-onset `ReturnStatus=-3` particles have clearly lower support than
same-frame nonfailed particles:

| group at first failure | all-neighbor proxy | specimen-neighbor proxy | support ratio to core |
| --- | ---: | ---: | ---: |
| `-3` failed | 88.0 | 56.0 | 0.618 |
| nearest nonfailed | 94.0 | 75.0 | 0.619 |
| same-region nonfailed | 94.6 | 66.5 | 0.705 |
| measurement core | 178.0 | 178.0 | 1.000 |

The `-3` support deficit is therefore real relative to the core and still
noticeable relative to same-region nonfailed particles.

The first-onset `ReturnStatus=-1` particles do not have worse support than
their nearest nonfailed neighbors.  Their main signature is different: near-zero
or negative `p'`.

## Local Kinematics

At first onset, `ReturnStatus=-3` particles have elevated local velocity
gradient and shear-rate proxies:

| group at first failure | velocity-gradient proxy | shear-rate proxy | DivVel |
| --- | ---: | ---: | ---: |
| `-3` failed | 0.112 | 0.156 | 0.03695 |
| nearest nonfailed | 0.090 | 0.128 | 0.02731 |
| same-region nonfailed | 0.075 | 0.105 | 0.02898 |
| measurement core | 0.027 | 0.038 | 0.02816 |

This supports the local strain-path interpretation for the line-search
failures.

The first-onset `ReturnStatus=-1` particles have much weaker kinematic
separation, but they carry strong negative `PorePressRate` and near-tension
effective stress.

## Local Stress Path

The first-onset `ReturnStatus=-3` particles are not near tension.  They have
positive `p'` but high return burden:

```text
p' ~= 73.97 Pa
q  ~= 93.76 Pa
q/p' ~= 1.27
yield residual ~= 3888
return iterations = 8
```

Compared with nearest nonfailed particles, the `-3` particles have much higher
`p'`, `q`, yield residual, and return burden:

```text
nearest nonfailed p' ~= 37.55 Pa
nearest nonfailed q  ~= 66.77 Pa
nearest nonfailed yield residual ~= 0
```

The first-onset `ReturnStatus=-1` particles are different:

```text
p' ~= -2.19 Pa
q  ~= 26.09 Pa
q/p' is negative/ill-conditioned
return iterations = 0
```

This confirms two local failure modes:

1. `-1`: inadmissible or near-tension `p'` states;
2. `-3`: positive `p'`, high local return burden, and line-search failure.

## Platen / Reaction Timing

Pairwise platen reaction remains bounded near onset.  There is no global force
blow-up synchronized with the first failure.  The failure is therefore not a
global axial-load instability; it is a local boundary-path problem.

The dense maps show that the problematic zone is where cap/platen proximity,
lateral surface truncation, and edge geometry interact.

## Interpretation

M3k supports the boundary-induced failure interpretation.

Evidence:

- onset captured in saved frames;
- failures remain concentrated in edge/cap/platen-adjacent regions;
- hardest `-3` particles have lower support and elevated local velocity
  gradients;
- `-1` particles show near-tension effective stress rather than MCC hardening
  corruption;
- `pc`, void ratio, plastic strains, reaction, and pore pressure remain bounded;
- no excluded particles or time-step burst occur.

This is not consistent with a global MCC sign-convention bug or global return
mapping collapse.

## Recommendations

Do not continue by only stacking more MCC return-mapping patches.  The next
minimum useful task should modify or test the boundary/geometry mechanism that
creates the local path:

1. first: platen/specimen interface smoothing;
2. second: edge/corner smoothing or edge diagnostic exclusion;
3. third: a smoother/fan-like cylinder layout closer to Zhao-style particle
   arrangements;
4. only return to local return-mapping patches if a smoothed boundary still
   produces the same failed local paths.

M3k does not justify a clean MCC validation package.  The MCC route remains a
CPU-only, feedback-off, reduced diagnostic until the boundary-induced
negative-status episodes are removed.

Full pore-pressure feedback and GPU MCC remain deferred.
