# M3j Boundary-Induced MCC Return Failure Report

## Objective

M3j-B is a postprocessing-only audit of the MCC return failures observed in
M3d2/M3f/M3h.  No source was modified, no new solver case was run, no GPU
simulation was run, and full pore-pressure feedback remained off.

The goal is to decide whether the remaining `ReturnStatus=-3` failures should
be treated primarily as:

1. global MCC return-mapping failure; or
2. boundary/platen/edge-induced local strain-path failure.

## Inputs and Outputs

Inputs:

- `M3d2_MCCReturnRobustness/m3d2_failed_return_particles.csv`
- `M3f_MCCReturnStagingRefinement/m3f_transient_failed_particles.csv`
- `M3h_MCCAdmissibleReturn/m3h_failed_return_state.csv`

M3j output directory:

`examples/u-pw/04_Undrained_Triaxial/experiments/M3j_BoundaryFailureAudit/`

Key outputs:

- `m3j_failed_particle_boundary_locations.csv`
- `m3j_failed_region_summary.csv`
- `m3j_local_strain_path_comparison.csv`
- `m3j_platen_interaction_failure_timeline.csv`
- `m3j_boundary_audit_summary.csv`
- `m3j_failed_particle_maps.svg/png`

## Are Failed Returns Boundary-Concentrated?

Yes.  Failed records are heavily concentrated in boundary/platen/edge regions.

Largest aggregate groups:

| source | boundary class | failed records | `-3` records | `-1` records |
| --- | --- | ---: | ---: | ---: |
| M3f | edge_corner | 2236 | 879 | 1357 |
| M3f | interior_ring | 966 | 661 | 305 |
| M3h | edge_corner | 946 | 218 | 728 |
| M3d2 | edge_corner | 768 | 104 | 664 |
| M3f | top_cap_zone | 656 | 648 | 8 |
| M3f | bottom_cap_zone | 647 | 455 | 192 |
| M3f | lateral_surface | 495 | 247 | 248 |

Measurement-core failures are rare:

```text
M3f measurement core: 42 records
M3d2 measurement core: 6 records
M3h measurement core: 5 records
```

This is strong evidence that the failure is not random or global.

## Bottom Platen, Edge, or Lateral Surface?

The most persistent trigger is the cap/lateral edge region.  Bottom fixed
platen adjacency is also a recurring trigger, especially in slower and cleaner
final-frame cases.  Top cap failures also appear strongly in ramp/adaptive
variants.

Best description:

```text
boundary-induced local return failure at cap/platen/edge regions,
with edge corners and bottom fixed-platen-adjacent particles as recurring
triggers.
```

The lateral surface participates, but it is not the only trigger.  The edge
where lateral confinement/free-surface selection meets cap/platen kinematics is
the key mixed-boundary zone.

## Are Local Strain / Stress Paths Abnormal?

The retained outputs do not include full local strain tensors or neighbor
counts, but available proxies support abnormal local paths:

- `-1` records have negative or near-zero saved `p'`, consistent with
  inadmissible/tension-side local states;
- `-3` records have positive `p'` but high `q/p'` and high return-iteration
  burden;
- slower loading reduces `DivVel`, velocity, and `PorePressRate` severity and
  clears final failures, but transient failures remain;
- `pc`, void ratio, and plastic strains remain bounded, so the issue is not
  global state corruption.

Representative M3h values:

```text
baseline -1: mean p'=-15.16 Pa, mean q=47.79 Pa
baseline -3: mean p'=43.23 Pa, mean q=83.94 Pa, mean q/p'=2.07
quarter-speed -3: mean p'=30.76 Pa, mean q=62.56 Pa, max |DivVel|=0.0202
```

This supports a local boundary strain/stress-path trigger.

## Platen Interaction

Pairwise platen reaction remains bounded during failures:

```text
baseline/admissible -3 reaction avg ~= 0.294 N
half-speed -3 reaction avg ~= 0.252 N
quarter-speed -3 reaction avg ~= 0.233 N
```

There is no evidence of global platen force blow-up.  The failure is local to
where material particles interact with the platen/edge boundary environment.

## Geometry Interpretation

The explicit platen workflow is a good direction and should not be replaced by
AccInput.  However, the reduced cylinder has sharp cap/lateral edge rings and
material particles immediately adjacent to fixed/prescribed platens.  In
Zhao-style triaxial/biaxial workflows, smooth/fan-like layouts and explicit
boundary layers matter because they reduce support and boundary-role
discontinuities.

The current reduced layout is adequate as a development benchmark, but not yet
as a strict clean MCC validation geometry.

## Should Return Mapping Continue to be Patched?

Not as the first priority.  M3d3/M3f/M3h already tried:

- fixed substepping;
- adaptive substepping;
- smoother loading;
- admissible line-search/backtracking;
- no-fallback rules.

These did not clean the saved-frame failures.  The next step should diagnose
and improve boundary/interface geometry and local strain paths before adding
more return-map complexity.

## Recommended Next Step

Recommended next task:

```text
M3k: very-short dense-output platen/edge diagnostic
```

Purpose:

- rerun only through early failure onset;
- keep feedback off and no GPU;
- output dense PartCsv around failure frames;
- compute neighbor counts, local support/completeness proxies, velocity
  gradients, and failed-vs-nearby-nonfailed comparisons;
- decide whether to smooth platen/specimen interface or rebuild a smoother
  cylinder/fan-like layout.

If M3k confirms boundary concentration, prioritize:

1. platen/specimen interface smoothing;
2. cap/edge transition improvement;
3. smooth/fan-like cylinder layout.

If M3k disproves the boundary interpretation, return to a deeper MCC local
return mapping redesign.

## Validation Status

The current route still cannot be called clean MCC validation:

- failures are local but still present;
- neighbor/local strain data are not yet complete;
- full u-pw feedback is off;
- true actuator reaction is not available;
- GPU MCC is unsupported.

M3g/M3i reporting can proceed only as caveated reduced reporting.  Clean MCC
validation should wait for a boundary-first diagnostic/fix.

Full pore-pressure feedback and GPU remain deferred.
