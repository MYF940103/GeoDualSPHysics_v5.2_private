# M3j Platen Interaction Failure Audit

## Objective

This audit checks whether MCC return failures synchronize with the explicit
platen workflow and platen-adjacent zones.  It uses retained M3f/M3h pairwise
reaction proxies and failed-return timestamps.

Generated output:

- `m3j_platen_interaction_failure_timeline.csv`

## Proximity to Platens

Failed records are strongly overrepresented near platen zones:

- bottom cap zone records occur at `z/H ~= 0.05` to `0.09`;
- top cap zone records occur at `z/H ~= 0.95` to `0.98`;
- edge-corner records combine cap proximity with lateral-surface proximity;
- measurement-core records are rare.

The bottom fixed platen remains important because quarter-speed and half-speed
cases still retain transient failures in edge/bottom-cap locations even when
the final frame is clean.

## Reaction Proxy Synchronization

M3f/M3h failed-record rows include the nearest pairwise platen reaction average
when available.  The reaction proxy remains bounded during failures:

- baseline/admissible-line `-3`: mean pairwise reaction about `0.294 N`;
- half-speed `-3`: mean pairwise reaction about `0.252 N`;
- quarter-speed `-3`: mean pairwise reaction about `0.233 N`.

There is no evidence of a global reaction blow-up.  The reaction stays smooth
while local return failures occur.  This suggests the failures arise from local
strain/stress concentration near platen/edge zones rather than from a global
platen-force instability.

## Top/Bottom Roles

The current explicit platen workflow has:

- bottom platen fixed;
- top platen prescribed velocity;
- lateral confinement applied to selected lateral specimen particles;
- specimen material particles near caps/edges still update MCC like interior
  particles.

This creates local zones where:

- fixed support suppresses vertical displacement;
- prescribed top motion imposes axial deformation;
- lateral free-surface/confinement selection changes near edge rings;
- material particles near cap/lateral corners can experience mixed axial,
  shear, and confinement effects.

The failed-return map is consistent with this mixed-boundary interpretation.

## Cap Leakage Diagnostic

Existing cap leakage diagnostics remain useful for detecting lateral selector
leakage into cap zones, but they do not describe:

- local platen/specimen strain concentration;
- edge-corner mixed boundary kinematics;
- per-particle neighbor support near the cap/lateral intersection;
- local contact/reaction distribution.

M3j therefore recommends a new edge/platen diagnostic before any strict clean
MCC validation claim.

## Bottom Platen as Trigger

The evidence supports bottom/platen-adjacent triggering but does not isolate it
as the only trigger:

- bottom-cap and edge-bottom records are persistent across M3d2/M3f/M3h;
- top-cap records are also prominent in ramp/adaptive variants;
- edge-corner records dominate in aggregate.

The most accurate description is:

```text
boundary-induced local return failure at cap/platen/edge regions,
with bottom fixed-platen and edge-corner zones as recurring triggers.
```

## Conclusion

The platen reaction is bounded, but failed MCC returns cluster where explicit
platen constraints and lateral-surface selection meet.  The failure is more
likely caused by local platen/edge strain paths than by global force imbalance.
