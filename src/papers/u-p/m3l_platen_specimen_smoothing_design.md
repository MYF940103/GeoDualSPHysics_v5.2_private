# M3l Platen / Specimen Smoothing Design

## Objective

M3l tests whether the MCC return failures identified in M3k are sensitive to
very small platen/specimen interface and edge/corner changes.  The goal is not
clean MCC validation.  The goal is to decide whether the remaining local
negative return statuses are driven by boundary geometry/support paths.

All M3l cases keep:

- `SoilConstitutiveModel=3`;
- mild MCC parameters from M3k;
- `PorePressureFeedback=0`;
- explicit top platen prescribed velocity;
- fixed bottom platen;
- lateral `FlexibleConfiningStress`;
- `SaveMccState=1`;
- `SavePlatenReactionDiagnostics=1`;
- dense output around first failure onset;
- CPU Release only.

No MCC return mapping, PR pressure update, FlexibleConfiningStress physics, or
GPU path is changed.

## Variant Family 1: Platen / Specimen Gap

This family lightly changes the initial top/bottom platen-to-specimen spacing.
The M3k XML uses a half-particle endpoint gap, but GenCase snaps the platen
particle centers to the dp grid.  The generated baseline particle centers have
an effective one-particle center gap:

```text
bottom platen upper particle center: z=-Dp
specimen bottom:   z=0
specimen top:      z=Hcyl
top platen lower particle center: z=Hcyl+Dp
```

M3l therefore tests a larger, generated two-particle center gap:

```text
bottom platen upper particle center: z=-2*Dp
top platen lower particle center: z=Hcyl+2*Dp
```

Purpose:

- reduce over-strong early platen/specimen kernel overlap;
- check whether first-onset `-3` and broad `-1` counts decrease.

Risk:

- too large a gap may reduce physical support and delay or weaken platen
  coupling.

## Variant Family 2: Platen Overhang / Interface Buffer

This family keeps the specimen radius but gives the platen a modest larger
radius:

```text
specimen radius: 0.03 m
platen radius:   0.04 m
```

Purpose:

- avoid a coincident platen/specimen sharp edge;
- improve support near the top/bottom edge/corner;
- test whether the first top-edge `ReturnStatus=-3` disappears or weakens.

Risk:

- the overhanging platen is still a reduced diagnostic, not a strict
  experimental platen-contact model;
- it may change the edge support path rather than solve the full geometry
  problem.

## Variant Family 3: Edge / Cap Selector Buffer

This family does not change particle geometry.  It increases the selected
lateral confinement cap/edge exclusion lengths:

```text
ConfiningStressCapExclusionLength:  0.015 -> 0.025
ConfiningStressEdgeExclusionLength: 0.015 -> 0.025
```

Purpose:

- reduce mixed cap/lateral confinement action near the sharp edge/corner;
- test whether the boundary-induced failure is tied to lateral confinement
  acting too close to platen/cap transitions.

Risk:

- this is a selector diagnostic, not a final physical geometry fix;
- if it helps, a better strict route would be geometric edge/corner smoothing
  or a smoother cylinder layout.

## Variant Family 4: Smooth / Fan-Like Cylinder Layout

This is the long-term strict route if the simple diagnostics confirm edge
support as the root cause.  It is not implemented in M3l.

Purpose:

- move toward Zhao-style smoother particle layouts;
- reduce support anisotropy and sharp cut-cell edge effects.

Risk:

- larger setup cost;
- changes too many baseline assumptions for this limited diagnostic stage.

## M3l Cases

M3l prepares and runs:

| case | purpose | geometry / selector change |
| --- | --- | --- |
| `CaseM3l_BaselineDense` | self-contained M3k reference | none |
| `CaseM3l_Gap2Dp` | platen/specimen spacing diagnostic | one-Dp generated gap -> two-Dp generated gap |
| `CaseM3l_PlatenOverhang` | interface edge support diagnostic | platen radius 0.04 m |
| `CaseM3l_EdgeSelectorBuffer` | edge/cap lateral selector diagnostic | cap/edge exclusion 0.025 m |

No additional MCC parameter combinations are introduced.

## Success Criteria

A smoothing variant is useful if it:

1. finishes `code=0`, `excluded=0`, `DtMin=0`;
2. reduces first-onset `ReturnStatus=-3`;
3. reduces or does not worsen `ReturnStatus=-1`;
4. improves failed-particle support/neighbor proxy;
5. lowers local velocity-gradient/shear proxy;
6. lowers local `q/p'` or return residual spikes;
7. leaves pairwise reaction, global p'-q path, and pore pressure bounded;
8. does not create a new failure region.

Clean MCC validation still requires all saved frames to have no negative return
status without fallback.  M3l is expected to remain diagnostic unless that gate
is clearly met.
