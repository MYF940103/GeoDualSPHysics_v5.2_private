# T4q Platen Boundary Implementation Plan

## Goal

T4q should replace the failed cap acceleration patch with a triaxial
platen-boundary prototype. The target is still elastic, CPU-first, and
diagnostic. DP and MCC remain deferred.

## Recommended T4q Route

1. Define explicit top/bottom platen groups.
2. Keep specimen soil material separate from platen particles.
3. Bottom platen is fixed.
4. Top platen has prescribed axial velocity or displacement.
5. Lateral soil surface uses `FlexibleConfiningStress`.
6. Platen particles are excluded from measurement and p-q statistics.
7. Pore-pressure feedback is either disabled at first or excluded from platen
   groups.
8. Axial force/reaction is output if possible.
9. Restart from all-surface isotropic equilibrium if the workflow can preserve
   the stress and pore-pressure state.

## XML-First Checks

Before source changes, T4q should check whether existing DualSPHysics XML
features can provide:

- fixed bottom `mkbound` platen;
- moving top `mkbound` platen with prescribed velocity;
- adequate interaction with the deformable u-pw soil material;
- motion scheduling after restart;
- output of platen motion and forces.

If this works, T4q can remain mostly XML/script/postprocessing.

## Likely Source Needs

If XML-only moving-boundary platens are not adequate, implement the smallest
source patch around a platen group:

- `PlatenBoundaryMode=0/1` default off;
- `TopPlatenMk` and `BottomPlatenMk`;
- prescribed velocity/displacement for top platen;
- fixed bottom platen;
- optional exclusion from stress/pore-pressure updates if platens are material
  proxies;
- reaction force accumulation;
- measurement tags or class output.

The patch must not modify the PR pressure equation or soil constitutive model.

## Output Fields Needed

T4q should plan to output:

- platen displacement and velocity;
- top/bottom reaction force;
- specimen-only axial strain;
- specimen-only p-q metrics;
- pore pressure in center/core regions;
- class/group membership for measurement exclusion.

## CPU/GPU

T4q remains CPU-only. GPU should hard-error for any new non-default platen
feature until the CPU route passes.

## Regression Tests

Minimum tests:

1. platen-only geometry/classification audit;
2. fixed bottom + prescribed top motion without hydromech feedback;
3. restart from Stage A all-surface equilibrium into platen-support stage;
4. lateral confinement retained, no axial loading;
5. very short top-platen velocity smoke only after the support stage is stable.

## No-Go Criteria

Do not proceed to axial baseline, DP, or MCC if:

- platen particles are not clearly separated from specimen material;
- reaction force cannot be interpreted;
- p-q metrics still include platen particles;
- restart loses stress or pore-pressure state;
- feedback-off support stage produces large `q` or large negative pressure;
- feedback-on confinement-only gate remains unstable.

## Expected Outcome

The expected useful outcome is not a full triaxial reproduction. It is a clean
mechanical boundary foundation: lateral flexible confinement plus explicit
top/bottom platen boundary layers.
